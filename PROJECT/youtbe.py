from googleapiclient.discovery import build
from textblob import TextBlob
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
import time

# --- API setup ---
api_key = ''  # Replace with your API key
youtube = build('youtube', 'v3', developerKey=api_key)

# --- Search for videos (up to 100) ---
def search_videos(query, total_results=100):
    video_info = []
    next_page_token = None

    while len(video_info) < total_results:
        max_results = min(50, total_results - len(video_info))
        search_response = youtube.search().list(
            q=query,
            part="snippet",
            type="video",
            maxResults=max_results,
            pageToken=next_page_token
        ).execute()

        for item in search_response['items']:
            video_info.append({
                'video_id': item['id']['videoId'],
                'title': item['snippet']['title']
            })

        next_page_token = search_response.get('nextPageToken')
        if not next_page_token:
            break

    return video_info

# --- Get video statistics and tags/keywords ---
def get_video_stats(video_ids):
    stats = []
    for i in range(0, len(video_ids), 50):
        batch = video_ids[i:i + 50]
        response = youtube.videos().list(
            part="statistics,snippet",
            id=",".join(batch)
        ).execute()

        for item in response['items']:
            statistics = item['statistics']
            snippet = item['snippet']
            stats.append({
                'Video ID': item['id'],
                'Video Title': snippet['title'],
                'Channel Name': snippet['channelTitle'],
                'Like Count': int(statistics.get('likeCount', 0)),
                'View Count': int(statistics.get('viewCount', 0)),
                'Comment Count': int(statistics.get('commentCount', 0)),
                'Title Length': len(snippet['title']),
                'Tags': ', '.join(snippet.get('tags', []))  # New: tags/keywords column
            })
    return stats

# --- Get top 10 comments with sentiment ---
def get_comments(video_id, video_title, max_comments=10):
    comments_data = []
    try:
        response = youtube.commentThreads().list(
            part='snippet',
            videoId=video_id,
            textFormat='plainText',
            maxResults=max_comments
        ).execute()

        for item in response['items']:
            comment_snippet = item['snippet']['topLevelComment']['snippet']
            comment = comment_snippet['textDisplay']
            author = comment_snippet['authorDisplayName']
            published = comment_snippet['publishedAt']
            like_count = comment_snippet['likeCount']
            reply_count = item['snippet']['totalReplyCount']

            # Sentiment analysis
            blob = TextBlob(comment)
            sentiment = blob.sentiment.polarity
            polarity = 'Positive' if sentiment > 0.1 else 'Negative' if sentiment < -0.1 else 'Neutral'

            comments_data.append({
                'Video ID': video_id,
                'Video Title': video_title,
                'Comment': comment,
                'Author': author,
                'Published At': published,
                'Comment Like Count': like_count,
                'Reply Count': reply_count,
                'Sentiment Score': sentiment,
                'Polarity': polarity,
                'Comment Length': len(comment)
            })
    except Exception as e:
        # Suppress noisy errors for disabled comments, but show others
        if "commentsDisabled" not in str(e):
            print(f"Error fetching comments for video {video_id}: {e}")
    return comments_data

# --- Main execution ---
start_time = time.time()

query = "gaming"
video_info_list = search_videos(query, total_results=100)

video_ids = [v['video_id'] for v in video_info_list]
video_stats = get_video_stats(video_ids)

def fetch_comments_wrapper(v):
    try:
        return get_comments(v['video_id'], v['title'], max_comments=10)
    except Exception as e:
        print(f"Error fetching comments for {v['video_id']}: {e}")
        return []

all_comments = []
skipped_comment_videos = 0

with ThreadPoolExecutor(max_workers=30) as executor:
    futures = [executor.submit(fetch_comments_wrapper, v) for v in video_info_list]
    for i, future in enumerate(as_completed(futures), 1):
        result = future.result()
        if not result:
            skipped_comment_videos += 1
        all_comments.extend(result)
        print(f"[{i}/{len(video_info_list)}] Comments fetched.")

# Convert to DataFrames
df_stats = pd.DataFrame(video_stats)
df_comments = pd.DataFrame(all_comments)

# --- Additional Calculated Columns ---
df_stats['Like-to-View Ratio'] = df_stats['Like Count'] / df_stats['View Count']
df_stats['Like-to-View Ratio'] = df_stats['Like-to-View Ratio'].replace([float('inf'), -float('inf')], 0).fillna(0)

# --- Calculate Average Comment Sentiment per Video ---
avg_sentiment = df_comments.groupby('Video ID')['Sentiment Score'].mean().reset_index()
avg_sentiment.rename(columns={'Sentiment Score': 'Avg Comment Sentiment'}, inplace=True)
df_stats = df_stats.merge(avg_sentiment, left_on='Video ID', right_on='Video ID', how='left')
df_stats['Avg Comment Sentiment'] = df_stats['Avg Comment Sentiment'].fillna(0)

# --- ML: Predictive Columns ---
def add_prediction_column(df, target, features, new_column_name):
    X = df[features]
    y = df[target]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    model = LinearRegression()
    model.fit(X_train, y_train)
    df[new_column_name] = model.predict(X)

# Predict with Linear Regression
add_prediction_column(df_stats, 'View Count', ['Title Length', 'Comment Count', 'Like Count'], 'Predicted Views')
add_prediction_column(df_stats, 'Like Count', ['Title Length', 'Comment Count', 'View Count'], 'Predicted Likes')
add_prediction_column(df_stats, 'Like-to-View Ratio', ['Title Length', 'Comment Count', 'View Count'], 'Predicted Like/View Ratio')

# Predict Comment Count using RandomForestRegressor
X = df_stats[['Title Length', 'Like Count', 'View Count']]
y = df_stats['Comment Count']
X_train, X_test, y_train, y_test = train_test_split(X, y, random_state=42)

rf_model = RandomForestRegressor()
rf_model.fit(X_train, y_train)

df_stats['Predicted Comments'] = rf_model.predict(X)
df_stats['Predicted Comments'] = df_stats['Predicted Comments'].clip(lower=0)

# Save final Excel
with pd.ExcelWriter('youtube_data_combined_gaming.xlsx') as writer:
    df_stats.to_excel(writer, sheet_name='Video Stats & Predictions', index=False)
    df_comments.to_excel(writer, sheet_name='Comments Sentiment', index=False)

print(f"\n✅ All processing complete. File saved as 'youtube_data_combined_gaming.xlsx'.")
print(f"⏱️ Total time taken: {time.time() - start_time:.2f} seconds")
print(f"Skipped comments for {skipped_comment_videos} videos due to disabled comments or errors.")
print(f"Total videos processed: {len(video_info_list)}")
print(f"Total comments fetched: {len(all_comments)}")