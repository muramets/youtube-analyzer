import streamlit as st
import re
import pandas as pd
from collections import Counter
from datetime import datetime
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

st.set_page_config(
    page_title="YouTube Video Analyzer",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Function to extract video ID from YouTube URL
def extract_video_id(url):
    # Regular expressions to match different YouTube URL formats
    patterns = [
        r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
        r'(?:embed\/)([0-9A-Za-z_-]{11})',
        r'(?:shorts\/)([0-9A-Za-z_-]{11})',
        r'(?:youtu\.be\/)([0-9A-Za-z_-]{11})'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

# Function to get video details from YouTube API
def get_video_details(api_key, video_ids):
    youtube = build('youtube', 'v3', developerKey=api_key)
    
    videos_data = []
    
    try:
        # Get video details for each video ID
        for video_id in video_ids:
            # Get video info
            video_response = youtube.videos().list(
                part='snippet,statistics',
                id=video_id
            ).execute()
            
            if 'items' in video_response and len(video_response['items']) > 0:
                video_item = video_response['items'][0]
                snippet = video_item['snippet']
                statistics = video_item['statistics']
                
                # Extract relevant information
                video_data = {
                    'id': video_id,
                    'title': snippet.get('title', ''),
                    'description': snippet.get('description', ''),
                    'tags': snippet.get('tags', []),
                    'thumbnail': snippet.get('thumbnails', {}).get('high', {}).get('url', ''),
                    'view_count': int(statistics.get('viewCount', 0)),
                    'published_at': snippet.get('publishedAt', '')
                }
                
                videos_data.append(video_data)
                
    except HttpError as e:
        st.error(f"An error occurred: {e}")
        
    return videos_data

# Function to tokenize text and remove common stop words
def tokenize_text(text):
    # More comprehensive URL pattern to remove URLs and their components
    url_pattern = r'(https?:\/\/)?(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)'
    
    # Remove all URLs completely
    text = re.sub(url_pattern, '', text, flags=re.IGNORECASE)
    
    # Remove common URL components that might be missed
    url_parts = ['http', 'https', 'www', 'com', 'net', 'org', 'io', 'html', 'php', 
                 'aspx', 'htm', 'spotify', 'youtube', 'youtu', 'soundcloud', 
                 'bandcamp', 'apple', 'music', 'itunes', 'fm', 'listen', 'playlists']
    
    # Convert to lowercase
    text = text.lower()
    
    # Common multi-word phrases to preserve as single tokens
    multi_word_phrases = ["hip hop", "lofi beats", "chill mix", "study music", 
                         "relaxing music", "sleep music", "ambient music", 
                         "background music", "piano music", "jazz music", 
                         "lofi chill", "chill out", "deep house"]
    
    # Replace spaces in multi-word phrases with underscores
    for phrase in multi_word_phrases:
        if phrase in text:
            text = text.replace(phrase, phrase.replace(' ', '_'))
    
    # Find all words
    words = re.findall(r'\b\w+\b', text)
    
    # Common stop words to filter out
    stop_words = {
        'a', 'an', 'the', 'and', 'or', 'but', 'if', 'because', 'as', 'what',
        'when', 'where', 'how', 'why', 'which', 'who', 'whom', 'this', 'that',
        'these', 'those', 'in', 'on', 'at', 'by', 'for', 'with', 'about',
        'against', 'between', 'into', 'through', 'during', 'before', 'after',
        'above', 'below', 'to', 'from', 'up', 'down', 'is', 'am', 'are',
        'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'having',
        'do', 'does', 'did', 'doing', 'i', 'you', 'he', 'she', 'it', 'we', 'they',
        'me', 'him', 'her', 'us', 'them', 'my', 'your', 'his', 'its', 'our', 'their',
        'can', 'could', 'will', 'would', 'shall', 'should', 'may', 'might', 'must'
    }
    
    # Add URL parts to stop words
    stop_words.update(url_parts)
    
    # Filter out stop words and short words
    filtered_words = [word.replace('_', ' ') if '_' in word else word 
                     for word in words if word not in stop_words and len(word) > 2]
    
    return filtered_words

# Function to analyze common and unique words
def analyze_words(videos_data):
    # Initialize dictionaries to store words from each video
    title_words_per_video = {}
    tag_words_per_video = {}
    desc_words_per_video = {}
    
    # Process each video
    for video in videos_data:
        video_id = video['id']
        
        # Process title
        title_words = tokenize_text(video['title'])
        title_words_per_video[video_id] = title_words
        
        # Process tags (tags are already in a list)
        tag_words_per_video[video_id] = [tag.lower() for tag in video.get('tags', [])]
        
        # Process description
        desc_words = tokenize_text(video['description'])
        desc_words_per_video[video_id] = desc_words
    
    # Count word occurrences across videos
    title_word_count = count_words_across_videos(title_words_per_video)
    tag_word_count = count_words_across_videos(tag_words_per_video)
    desc_word_count = count_words_across_videos(desc_words_per_video)
    
    return {
        'title_analysis': {
            'words_per_video': title_words_per_video,
            'word_count': title_word_count
        },
        'tag_analysis': {
            'words_per_video': tag_words_per_video,
            'word_count': tag_word_count
        },
        'desc_analysis': {
            'words_per_video': desc_words_per_video,
            'word_count': desc_word_count
        },
    }

# Count how many videos contain each word
def count_words_across_videos(words_per_video):
    all_videos = set(words_per_video.keys())
    word_count = {}
    
    for video_id, words in words_per_video.items():
        for word in set(words):  # Use set to count each word once per video
            if word not in word_count:
                word_count[word] = set()
            word_count[word].add(video_id)
    
    # Convert sets to counts
    return {word: (len(videos), list(videos)) for word, videos in word_count.items()}

# Format datetime string to human-readable format
def format_datetime(datetime_str):
    try:
        dt = datetime.strptime(datetime_str, "%Y-%m-%dT%H:%M:%SZ")
        return dt.strftime("%B %d, %Y at %I:%M %p")
    except:
        return datetime_str

# Main application
def main():
    # Sidebar for API key
    with st.sidebar:
        st.title("📊 YouTube Video Analyzer")
        api_key = st.text_input("Enter your YouTube API Key", type="password")
        st.markdown("---")
        st.info("This app analyzes multiple YouTube videos and finds common elements between them.")
        st.markdown("1. Enter your YouTube API key")
        st.markdown("2. Add YouTube video URLs")
        st.markdown("3. Click 'Analyze Videos' to see results")

    # Main content
    st.title("🎬 YouTube Video Comparison Tool")
    
    # Initialize session state for URLs
    if 'video_urls' not in st.session_state:
        st.session_state.video_urls = [""]
    
    # Function to add more URL fields
    def add_url_field():
        st.session_state.video_urls.append("")
    
    # URL input section
    st.subheader("Add YouTube Videos")
    
    # Function to remove URL field
    def remove_url_field():
        if len(st.session_state.video_urls) > 1:
            st.session_state.video_urls.pop()
    
    # Display URL input fields
    for i, url in enumerate(st.session_state.video_urls):
        col1, col2 = st.columns([6, 1])
        with col1:
            st.session_state.video_urls[i] = st.text_input(
                f"Video URL {i+1}", 
                value=url,
                key=f"url_{i}"
            )
        if i == len(st.session_state.video_urls) - 1:
            with col2:
                # Show Add button by default for the first field or if field has content
                # Show Delete button if it's not the first field and is empty
                if i == 0 or url.strip():
                    st.button("➕ Add Video", on_click=add_url_field)
                else:
                    st.button("❌ Delete", on_click=remove_url_field)
    
    # Analyze button
    analyze_clicked = st.button("Analyze Videos", type="primary")
    
    # Process videos when button is clicked
    if analyze_clicked:
        if not api_key:
            st.error("Please enter your YouTube API key in the sidebar.")
        else:
            # Filter out empty URLs
            valid_urls = [url for url in st.session_state.video_urls if url.strip()]
            
            if not valid_urls:
                st.warning("Please add at least one YouTube video URL.")
            else:
                with st.spinner("Analyzing videos..."):
                    # Extract video IDs
                    video_ids = []
                    for url in valid_urls:
                        video_id = extract_video_id(url.strip())
                        if video_id:
                            video_ids.append(video_id)
                        else:
                            st.warning(f"Could not extract video ID from URL: {url}")
                    
                    if video_ids:
                        # Get video details
                        videos_data = get_video_details(api_key, video_ids)
                        
                        if videos_data:
                            # Store in session state for later use
                            st.session_state.videos_data = videos_data
                            st.session_state.analysis_results = analyze_words(videos_data)
                            st.success(f"Successfully analyzed {len(videos_data)} videos!")
                        else:
                            st.error("Failed to retrieve video data. Please check your API key and try again.")
                    else:
                        st.error("No valid YouTube video IDs found in the provided URLs.")
    
    # Display analysis if data is available
    if 'videos_data' in st.session_state and 'analysis_results' in st.session_state:
        videos_data = st.session_state.videos_data
        analysis_results = st.session_state.analysis_results
        total_videos = len(videos_data)
        
        st.markdown("---")
        st.subheader("🔍 Analysis Results")
        
        # Create tabs for the different analysis sections
        tab1, tab2, tab3 = st.tabs(["Titles", "Tags", "Descriptions"])
        
        with tab1:
            st.subheader("Common Words in Titles")
            title_df = create_word_frequency_df(
                analysis_results['title_analysis']['word_count'], 
                total_videos
            )
            if not title_df.empty:
                st.dataframe(title_df, height=300)
            else:
                st.info("No common words found in titles.")
        
        with tab2:
            st.subheader("Common Tags")
            tag_df = create_word_frequency_df(
                analysis_results['tag_analysis']['word_count'],
                total_videos
            )
            if not tag_df.empty:
                st.dataframe(tag_df, height=300)
            else:
                st.info("No common tags found.")
        
        with tab3:
            st.subheader("Common Words in Descriptions")
            desc_df = create_word_frequency_df(
                analysis_results['desc_analysis']['word_count'],
                total_videos
            )
            if not desc_df.empty:
                st.dataframe(desc_df, height=300)
            else:
                st.info("No common words found in descriptions.")
        
        # Individual video details
        st.markdown("---")
        st.subheader("📽️ Individual Video Details")
        
        for i, video in enumerate(videos_data):
            # Create a container for each video
            video_container = st.container()
            
            with video_container:
                # Add HTML anchor for navigation from tables
                st.markdown(f"<div id='video-{i+1}'></div>", unsafe_allow_html=True)
                
                # Display title with link (smaller heading)
                st.markdown(f"#### {i+1}. {video['title']} ([Link](https://www.youtube.com/watch?v={video['id']}))")
                
                # Create columns for thumbnail and metadata
                thumb_col, meta_col = st.columns([1, 3])
                
                # Display thumbnail with fixed width
                with thumb_col:
                    st.image(video['thumbnail'], width=240)
                
                # Display metadata
                with meta_col:
                    st.write(f"**Published:** {format_datetime(video['published_at'])}")
                    st.write(f"**Views:** {video['view_count']:,}")
                
                # Tags expander with comma-separated list
                if video.get('tags'):
                    with st.expander("Tags"):
                        tags_list = []
                        
                        for tag in video.get('tags', []):
                            tag_lower = tag.lower()
                            videos_with_tag = []
                            
                            # Check if this tag is in other videos
                            if tag_lower in analysis_results['tag_analysis']['word_count'] and len(analysis_results['tag_analysis']['word_count'][tag_lower][1]) > 1:
                                video_ids = analysis_results['tag_analysis']['word_count'][tag_lower][1]
                                
                                # Create list of videos with this tag (excluding current)
                                for video_id in video_ids:
                                    if video_id != video['id']:
                                        video_idx = next((idx for idx, v in enumerate(videos_data) if v['id'] == video_id), None)
                                        if video_idx is not None:
                                            videos_with_tag.append(f"Video {video_idx+1}")
                                
                                # Common tag with highlighting
                                if videos_with_tag:
                                    tags_list.append(f'<span style="color: #006400; font-weight: bold;" title="Also in: {", ".join(videos_with_tag)}">{tag}</span>')
                                else:
                                    tags_list.append(tag)
                            else:
                                tags_list.append(tag)
                        
                        # Join tags with commas
                        tags_html = ", ".join(tags_list)
                        st.markdown(tags_html, unsafe_allow_html=True)
                
                # Description expander (YouTube-style)
                if video.get('description'):
                    with st.expander("Description"):
                        render_highlighted_description(
                            video['description'],
                            analysis_results['desc_analysis']['word_count'],
                            video['id'],
                            videos_data
                        )
                
                # Add separator between videos
                st.markdown("---")

# Create a DataFrame for word frequencies
def create_word_frequency_df(word_count, total_videos):
    if not word_count:
        return pd.DataFrame()
    
    # Get videos_data from session state
    videos_data = st.session_state.videos_data
    
    # Create dataframe
    data = []
    for word, (count, video_ids) in word_count.items():
        if count > 1:  # Only include words that appear in more than one video
            # Create list of video URLs
            video_urls = []
            for video_id in video_ids:
                for video in videos_data:
                    if video['id'] == video_id:
                        video_urls.append(f"https://www.youtube.com/watch?v={video['id']}")
                        break
            
            # Join with commas
            videos_text = ", ".join(video_urls)
            
            data.append({
                'Word': word,
                'Frequency': f"{count} out of {total_videos}",
                'Videos': videos_text,
                'Count': count  # For sorting
            })
    
    if not data:
        return pd.DataFrame()
    
    df = pd.DataFrame(data)
    df = df.sort_values(by='Count', ascending=False).drop('Count', axis=1).reset_index(drop=True)
    # Reset index to start from 1 instead of 0
    df.index = df.index + 1
    
    return df

# Function to render highlighted text for tags
def render_highlighted_text(tags, word_count, current_video_id, videos_data, is_tag=False):
    for tag in tags:
        tag_lower = tag.lower()
        videos_with_tag = []
        
        # Check if this tag is in other videos
        if tag_lower in word_count and len(word_count[tag_lower][1]) > 1:
            video_ids = word_count[tag_lower][1]
            
            # Create list of videos with this tag (excluding current)
            for i, video_id in enumerate(video_ids):
                if video_id != current_video_id:
                    video_idx = next((idx for idx, v in enumerate(videos_data) if v['id'] == video_id), None)
                    if video_idx is not None:
                        videos_with_tag.append(f"Video {video_idx+1}")
            
            # Display highlighted tag with tooltip
            if videos_with_tag:
                st.markdown(
                    f"<span style='color: #006400; font-weight: bold;' "
                    f"title='Also in: {', '.join(videos_with_tag)}'>{tag}</span>",
                    unsafe_allow_html=True
                )
            else:
                st.write(tag)
        else:
            st.write(tag)

# Function to render highlighted description
def render_highlighted_description(description, word_count, current_video_id, videos_data):
    # Tokenize description
    words = re.findall(r'\b\w+\b', description.lower())
    processed_words = set()
    
    # Create a map of common words with their videos
    common_words = {}
    for word, (count, video_ids) in word_count.items():
        if count > 1 and word not in processed_words:
            videos_with_word = []
            for video_id in video_ids:
                if video_id != current_video_id:
                    video_idx = next((idx for idx, v in enumerate(videos_data) if v['id'] == video_id), None)
                    if video_idx is not None:
                        videos_with_word.append(f"Video {video_idx+1}")
            
            if videos_with_word:
                common_words[word] = videos_with_word
                processed_words.add(word)
    
    # Split description into paragraphs and process each
    paragraphs = description.split('\n')
    for paragraph in paragraphs:
        if not paragraph.strip():
            st.write("")
            continue
        
        html_paragraph = paragraph
        
        # Highlight common words
        for word, videos in common_words.items():
            # Create regex pattern to match whole word case-insensitively
            pattern = rf'\b({re.escape(word)})\b'
            
            # Replace with highlighted version
            replacement = f"<span style='color: #006400; font-weight: bold;' title='Also in: {', '.join(videos)}'>\\1</span>"
            html_paragraph = re.sub(pattern, replacement, html_paragraph, flags=re.IGNORECASE)
        
        # Display the processed paragraph
        st.markdown(html_paragraph, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
