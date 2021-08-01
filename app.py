from apiclient.discovery import build
# from apiclient.errors import HttpError
# from oauth2client.tools import argparser
import streamlit as st
import pandas as pd

DEVELOPER_KEY = st.secrets['KEY']
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"

youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION,
  developerKey=DEVELOPER_KEY)



def video_search(youtube, q='自動化', max_results=50):
    # search.listメソッドを呼び出して、指定したクエリ用語にマッチする # 結果を取得します。
    # クエリ用語にマッチする結果を取得します。
    response = youtube.search().list(
      q=q,
      part="id,snippet",
      order='viewCount',
      type='video',
      maxResults=max_results
    ).execute()

    items = response['items']
    items_id = []
    for item in items:
        item_id = {}
        item_id['video_id'] = item['id']['videoId']
        item_id['channel_id'] = item['snippet']['channelId']
        items_id.append(item_id)

    df_video = pd.DataFrame(items_id)
    return df_video


def get_results(df_video, threshold=10000):
    channel_ids = df_video['channel_id'].unique().tolist()

    subscriber_list = youtube.channels().list(
      id=','.join(channel_ids),
      part='statistics',
      fields='items(id, statistics(subscriberCount))'
    ).execute()

    subscribers = []
    for item in subscriber_list['items']:
        subscriber = {}
        if len(item['statistics']) > 0:
            subscriber['channel_id'] = item['id']
            subscriber['subscriber_count'] = int(item['statistics']['subscriberCount'])
        else:
            subscriber['channel_id'] = item['id']
        subscribers.append(subscriber)

    df_subscribers = pd.DataFrame(subscribers)
    df = pd.merge(left=df_video, right=df_subscribers, on='channel_id')
    df_extracted = df[df['subscriber_count'] < threshold]

    video_ids = df_extracted['video_id'].tolist()
    video_list = youtube.videos().list(
      id=','.join(video_ids),
      part='snippet, statistics',
      fields='items(id,snippet(title) , statistics(viewCount))'
    ).execute()

    videos = []
    for item in video_list['items']:
        video = {}
        video['video_id'] = item['id']
        video['title'] = item['snippet']['title']
        video['view_count'] = int(item['statistics']['viewCount'])
        videos.append(video)

    df_video_info = pd.DataFrame(videos)
    results = pd.merge(left=df_extracted, right=df_video_info, on='video_id')
    results = results.loc[:, ['video_id', 'title',
                            'view_count', 'subscriber_count', 'channel_id']]
    return results


st.title('YouTube分析アプリ')

st.sidebar.write('## クエリとしきい値の設定')
st.sidebar.write('## クエリの入力')
query = st.sidebar.text_input('検索クエリを入力してください', 'Python 自動化')

st.sidebar.write('## しきい値の設定')
threshold = st.sidebar.slider('登録者のしきい値', 100, 100000, 5000)

st.write('### 選択中のパラメータ')
st.markdown(f'''
- 検索クエリ： {query}
- 登録者の閾値： {threshold}
''')

df_video = video_search(youtube, q=query, max_results=50)
results = get_results(df_video, threshold=threshold)

st.write('### 分析結果', results)
st.write('### 動画再生')

video_id = st.text_input('動画IDを入力してください')
url = f'https://youtu.be/{video_id}'

video_field = st.empty()
video_field.write('こちらに動画が表示されます')

if st.button('動画表示'):
    if len(video_id) > 0:
        try:
            video_field.video(url)
        except:
            st.error('おっと！なにかエラーが出てしまいました！')