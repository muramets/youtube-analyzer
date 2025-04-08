import streamlit as st
import re
import pandas as pd
from googleapiclient.discovery import build
from collections import Counter
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize

# Set page title and configuration
st.set_page_config(
    page_title="YouTube Video Analyzer",
    page_icon="🎬",
    layout="wide"
)

# Apply CSS for highlighting and sidebar width
st.markdown("""
<style>
    /* Highlight matching elements with green text color */
    .highlight {
        color: #008000 !important;
        font-weight: 500 !important;
    }
    
    /* Set sidebar width to 350px */
    [data-testid="stSidebar"] {
        width: 350px !important;
        min-width: 350px !important;
        max-width: 350px !important;
    }
    
    /* Adjust sidebar content to fit sidebar */
    [data-testid="stSidebar"] > div:first-child {
        width: 350px !important;
        min-width: 350px !important;
    }
    
    /* Make sure text wraps properly in the sidebar */
    [data-testid="stSidebar"] .stMarkdown, 
    [data-testid="stSidebar"] .stTextInput {
        word-wrap: break-word !important;
    }
</style>
""", unsafe_allow_html=True)
# Initialize YouTube API client
def get_youtube_client():
    # Get API key from session state
    api_key = st.session_state.get('youtube_api_key', '')
    if not api_key:
        st.error("Please enter your YouTube API Key in the sidebar.")
        st.stop()
    return build('youtube', 'v3', developerKey=api_key)

# Extract video ID from YouTube URL
def extract_video_id(url):
    # Regular expressions to match various YouTube URL formats
    patterns = [
        r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',  # Standard YouTube URLs
        r'(?:embed\/)([0-9A-Za-z_-]{11})',  # Embedded URLs
        r'(?:youtu\.be\/)([0-9A-Za-z_-]{11})'  # Shortened youtu.be URLs
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    return None

# Fetch video details from YouTube API
def get_video_details(video_id):
    try:
        youtube = get_youtube_client()
        
        # Get video details
        video_response = youtube.videos().list(
            part='snippet,statistics',
            id=video_id
        ).execute()
        
        if not video_response['items']:
            return None
        
        video_data = video_response['items'][0]
        snippet = video_data['snippet']
        statistics = video_data['statistics']
        
        # Extract relevant information
        video_info = {
            'video_id': video_id,  # Include video_id for generating links
            'title': snippet['title'],
            'publication_date': snippet['publishedAt'].split('T')[0],  # Format date
            'views': int(statistics.get('viewCount', 0)),
            'description': snippet.get('description', ''),
            'tags': snippet.get('tags', []),
            'thumbnail': snippet['thumbnails']['high']['url']
        }
        
        return video_info
    
    except Exception as e:
        st.error(f"Error fetching video details: {str(e)}")
        return None

# Format date to human-readable format
def format_date(date_str):
    from datetime import datetime
    date_obj = datetime.strptime(date_str, '%Y-%m-%d')
    return date_obj.strftime('%d %b %Y')

# Find common tags across videos (appearing in at least 2 videos)
def find_common_tags(videos_data):
    if not videos_data or len(videos_data) < 2:
        return [], 0, {}
    
    # Collect all unique tags across all videos
    all_tags = set()
    for video in videos_data:
        all_tags.update(video['tags'])
    
    # Count occurrences of each tag
    tag_counts = {}
    for video in videos_data:
        for tag in set(video['tags']):  # Use set to count each tag only once per video
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
    
    # Find tags that appear in at least 2 videos
    common_tags = {tag: count for tag, count in tag_counts.items() if count >= 2}
    
    # Find tags that appear in only one video (non-overlapping)
    unique_tags = {tag: count for tag, count in tag_counts.items() if count == 1}
    
    # Calculate percentage of common tags out of all unique tags
    result = []
    overall_percentage = 0
    
    if all_tags:
        overall_percentage = (len(common_tags) / len(all_tags)) * 100
        
        # Create result list with individual tag info and count
        for tag, count in sorted(common_tags.items(), key=lambda x: x[1], reverse=True):
            result.append((tag, count, len(videos_data)))
    
    return result, overall_percentage, unique_tags

# Download all required NLTK resources
def download_nltk_resources():
    resources = ['punkt', 'stopwords', 'punkt_tab']
    for resource in resources:
        try:
            nltk.data.find(f'tokenizers/{resource}')
        except LookupError:
            nltk.download(resource)

# Find common words in descriptions (appearing in at least 2 videos)
def find_common_words(videos_data, min_frequency=2):
    if not videos_data or len(videos_data) < 2:
        return [], 0, {}
    
    # Download NLTK resources if not already downloaded
    download_nltk_resources()
    
    # Process descriptions
    all_descriptions = [video['description'] for video in videos_data]
    
    # Tokenize and clean words
    all_words_lists = []
    all_unique_words = set()
    stop_words = set(stopwords.words('english') + stopwords.words('russian'))
    
    # Store words for each video
    video_words = []
    
    for description in all_descriptions:
        # Tokenize
        words = word_tokenize(description.lower())
        
        # Filter out stopwords, punctuation, and short words
        filtered_words = [
            word for word in words 
            if word.isalpha() and word not in stop_words and len(word) > 2
        ]
        
        video_words.append(set(filtered_words))
        all_unique_words.update(filtered_words)
    
    # Count occurrences of each word across videos
    word_counts = {}
    for words in video_words:
        for word in words:
            word_counts[word] = word_counts.get(word, 0) + 1
    
    # Find words that appear in at least 2 videos
    common_words = {word: count for word, count in word_counts.items() if count >= 2}
    
    # Find words that appear in only one video (non-overlapping)
    unique_words = {word: count for word, count in word_counts.items() if count == 1}
    
    # Calculate percentage of common words out of all unique words
    result = []
    overall_percentage = 0
    
    if all_unique_words:
        overall_percentage = (len(common_words) / len(all_unique_words)) * 100
        
        # Create result list with individual word info and count
        for word, count in sorted(common_words.items(), key=lambda x: x[1], reverse=True):
            result.append((word, count, len(videos_data)))
    
    return result, overall_percentage, unique_words

# Find common words in titles (appearing in at least 2 videos)
def find_common_title_words(videos_data):
    if not videos_data or len(videos_data) < 2:
        return [], 0, {}
    
    # Download NLTK resources if not already downloaded
    download_nltk_resources()
    
    # Process titles
    all_titles = [video['title'] for video in videos_data]
    
    # Tokenize and clean words
    all_words_lists = []
    all_unique_words = set()
    stop_words = set(stopwords.words('english') + stopwords.words('russian'))
    
    # Store words for each video
    video_words = []
    
    for title in all_titles:
        # Tokenize
        words = word_tokenize(title.lower())
        
        # Filter out stopwords, punctuation, and short words
        filtered_words = [
            word for word in words 
            if word.isalpha() and word not in stop_words and len(word) > 2
        ]
        
        video_words.append(set(filtered_words))
        all_unique_words.update(filtered_words)
    
    # Count occurrences of each word across videos
    word_counts = {}
    for words in video_words:
        for word in words:
            word_counts[word] = word_counts.get(word, 0) + 1
    
    # Find words that appear in at least 2 videos
    common_words = {word: count for word, count in word_counts.items() if count >= 2}
    
    # Find words that appear in only one video (non-overlapping)
    unique_words = {word: count for word, count in word_counts.items() if count == 1}
    
    # Calculate percentage of common words out of all unique words
    result = []
    overall_percentage = 0
    
    if all_unique_words:
        overall_percentage = (len(common_words) / len(all_unique_words)) * 100
        
        # Create result list with individual word info and count
        for word, count in sorted(common_words.items(), key=lambda x: x[1], reverse=True):
            result.append((word, count, len(videos_data)))
    
    return result, overall_percentage, unique_words

# Function to generate Excel file with recommendations
def generate_excel_file(videos_data, common_title_words, common_tags, common_words, 
                       unique_title_words, unique_tags, unique_desc_words):
    import pandas as pd
    from io import BytesIO
    import importlib.util
    
    # Check if openpyxl is available
    openpyxl_available = importlib.util.find_spec("openpyxl") is not None
    
    # Create a BytesIO object to store the Excel file
    output = BytesIO()
    
    try:
        # Create DataFrames for each section
        # Video links
        video_links = []
        for video in videos_data:
            video_id = video.get('video_id', '')
            title = video.get('title', '')
            if video_id:
                link = f"https://www.youtube.com/watch?v={video_id}"
                video_links.append({'Title': title, 'Link': link})
        
        # Common title words
        title_words_data = [{'Common Title Words': word, 'Appears in': f"{count} out of {total} videos"} 
                           for word, count, total in common_title_words] if common_title_words else []
        
        # Common tags
        tags_data = [{'Common Tags': tag, 'Appears in': f"{count} out of {total} videos"} 
                    for tag, count, total in common_tags] if common_tags else []
        
        # Common description words
        words_data = [{'Common Description Words': word, 'Appears in': f"{count} out of {total} videos"} 
                     for word, count, total in common_words] if common_words else []
        
        # Create Excel file with pandas
        if openpyxl_available:
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                # Video links
                if video_links:
                    df = pd.DataFrame(video_links)
                    df.to_excel(writer, sheet_name='Video Links', index=False)
                    
                    # Get the worksheet to add hyperlinks and adjust column widths
                    worksheet = writer.sheets['Video Links']
                    
                    # Add hyperlinks to the Link column
                    for idx, row in enumerate(video_links, start=2):  # start=2 because Excel is 1-indexed and we have a header row
                        cell = worksheet.cell(row=idx, column=2)  # Column B (Link)
                        cell.hyperlink = row['Link']
                        cell.style = 'Hyperlink'
                    
                    # Adjust column widths based on content
                    for column in worksheet.columns:
                        max_length = 0
                        column_letter = column[0].column_letter
                        for cell in column:
                            try:
                                if len(str(cell.value)) > max_length:
                                    max_length = len(str(cell.value))
                            except:
                                pass
                        adjusted_width = (max_length + 2) * 1.2
                        worksheet.column_dimensions[column_letter].width = adjusted_width
                
                # Common title words
                if title_words_data:
                    df = pd.DataFrame(title_words_data)
                    df.to_excel(writer, sheet_name='Common Title Words', index=False)
                    
                    # Adjust column widths
                    worksheet = writer.sheets['Common Title Words']
                    for column in worksheet.columns:
                        max_length = 0
                        column_letter = column[0].column_letter
                        for cell in column:
                            try:
                                if len(str(cell.value)) > max_length:
                                    max_length = len(str(cell.value))
                            except:
                                pass
                        adjusted_width = (max_length + 2) * 1.2
                        worksheet.column_dimensions[column_letter].width = adjusted_width
                
                # Common tags
                if tags_data:
                    df = pd.DataFrame(tags_data)
                    df.to_excel(writer, sheet_name='Common Tags', index=False)
                    
                    # Adjust column widths
                    worksheet = writer.sheets['Common Tags']
                    for column in worksheet.columns:
                        max_length = 0
                        column_letter = column[0].column_letter
                        for cell in column:
                            try:
                                if len(str(cell.value)) > max_length:
                                    max_length = len(str(cell.value))
                            except:
                                pass
                        adjusted_width = (max_length + 2) * 1.2
                        worksheet.column_dimensions[column_letter].width = adjusted_width
                
                # Common description words
                if words_data:
                    df = pd.DataFrame(words_data)
                    df.to_excel(writer, sheet_name='Common Description Words', index=False)
                    
                    # Adjust column widths
                    worksheet = writer.sheets['Common Description Words']
                    for column in worksheet.columns:
                        max_length = 0
                        column_letter = column[0].column_letter
                        for cell in column:
                            try:
                                if len(str(cell.value)) > max_length:
                                    max_length = len(str(cell.value))
                            except:
                                pass
                        adjusted_width = (max_length + 2) * 1.2
                        worksheet.column_dimensions[column_letter].width = adjusted_width
        else:
            # Fallback to CSV if openpyxl is not available
            all_data = pd.DataFrame()
            
            # Add video links
            if video_links:
                all_data = pd.concat([all_data, pd.DataFrame([['VIDEO LINKS']])], ignore_index=True)
                all_data = pd.concat([all_data, pd.DataFrame(video_links)], ignore_index=True)
                all_data = pd.concat([all_data, pd.DataFrame([['---']])], ignore_index=True)
            
            # Add common title words
            if title_words_data:
                all_data = pd.concat([all_data, pd.DataFrame([['COMMON TITLE WORDS']])], ignore_index=True)
                all_data = pd.concat([all_data, pd.DataFrame(title_words_data)], ignore_index=True)
                all_data = pd.concat([all_data, pd.DataFrame([['---']])], ignore_index=True)
            
            # Add common tags
            if tags_data:
                all_data = pd.concat([all_data, pd.DataFrame([['COMMON TAGS']])], ignore_index=True)
                all_data = pd.concat([all_data, pd.DataFrame(tags_data)], ignore_index=True)
                all_data = pd.concat([all_data, pd.DataFrame([['---']])], ignore_index=True)
            
            # Add common description words
            if words_data:
                all_data = pd.concat([all_data, pd.DataFrame([['COMMON DESCRIPTION WORDS']])], ignore_index=True)
                all_data = pd.concat([all_data, pd.DataFrame(words_data)], ignore_index=True)
            
            # Write to CSV
            all_data.to_csv(output, index=False)
    
    except Exception as e:
        st.error(f"Error generating Excel file: {str(e)}")
        # Create a simple text file as fallback
        output = BytesIO()
        output.write(b"Error generating Excel file. Please make sure you have openpyxl installed.")
        output.seek(0)
    
    # Reset pointer to start of file
    output.seek(0)
    return output

# Main application
def main():
    # Ensure NLTK resources are downloaded at startup
    download_nltk_resources()
    
    # Create sidebar for API key input
    with st.sidebar:
        st.title("Settings")
        
        # Initialize API key in session state if not exists
        if 'youtube_api_key' not in st.session_state:
            st.session_state.youtube_api_key = ""
            
        # API key input
        api_key = st.text_input(
            "YouTube API Key",
            value=st.session_state.youtube_api_key,
            type="password",
            help="Enter your YouTube API Key. If you don't have one, you can get it from the Google Cloud Console."
        )
        
        # Update session state when API key changes
        if api_key != st.session_state.youtube_api_key:
            st.session_state.youtube_api_key = api_key
            
        # Add instructions for getting an API key
        with st.expander("How to get a YouTube API Key"):
            st.markdown("""
            1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
            2. Create a new project or select an existing one
            3. Enable the YouTube Data API v3
            4. Create credentials (API key)
            5. Copy the API key and paste it above
            """)
    
    # Display content directly without a separate container
    st.title("YouTube Video Analyzer")
    st.write("Enter YouTube video URLs to analyze common patterns and details.")
    
    # Initialize session state for storing analysis results
    if 'download_clicked' not in st.session_state:
        st.session_state.download_clicked = False
    
    if 'analysis_complete' not in st.session_state:
        st.session_state.analysis_complete = False
        
    if 'videos_data' not in st.session_state:
        st.session_state.videos_data = []
        
    if 'common_title_words' not in st.session_state:
        st.session_state.common_title_words = []
        st.session_state.title_words_percentage = 0
        
    if 'common_tags' not in st.session_state:
        st.session_state.common_tags = []
        st.session_state.tags_percentage = 0
        
    if 'common_words' not in st.session_state:
        st.session_state.common_words = []
        st.session_state.words_percentage = 0
    
    # Initialize session state for URL inputs if not exists
    if 'url_inputs' not in st.session_state:
        st.session_state.url_inputs = [""]  # Start with one input field
    
    # Function to add a new URL input field
    def add_url_input():
        st.session_state.url_inputs.append("")
    
    # Display URL input fields
    urls = []
    for i, default_value in enumerate(st.session_state.url_inputs):
        # Create columns for input and remove button
        col1, col2 = st.columns([6, 1])
        with col1:
            url = st.text_input(
                f"YouTube URL {i+1}",
                value=default_value,
                key=f"url_{i}"
            )
            urls.append(url)
        
        # Only show remove button if there's more than one input
        if i > 0:
            with col2:
                if st.button("➖", key=f"remove_{i}"):
                    st.session_state.url_inputs.pop(i)
                    st.rerun()
    
    # Add URL button
    if st.button("➕ Add Another URL"):
        add_url_input()
        st.rerun()
    
    # Analyze button
    if st.button("🔍 Analyze Videos"):
        # Reset analysis state when new analysis is requested
        st.session_state.analysis_complete = False
        st.session_state.download_clicked = False
        
        # Filter out empty URLs
        valid_urls = [url for url in urls if url.strip()]
        
        if not valid_urls:
            st.warning("Please enter at least one YouTube URL.")
            return
        
        with st.spinner("Analyzing videos..."):
            # Process each URL
            videos_data = []
            invalid_urls = []
            
            for url in valid_urls:
                video_id = extract_video_id(url)
                if not video_id:
                    invalid_urls.append(url)
                    continue
                
                video_info = get_video_details(video_id)
                if video_info:
                    videos_data.append(video_info)
            
            # Show warnings for invalid URLs
            if invalid_urls:
                st.warning(f"Could not process {len(invalid_urls)} URL(s). Please check they are valid YouTube URLs.")
            
            if not videos_data:
                st.error("No valid videos to analyze.")
                return
            
            # Find common elements
            common_title_words, title_words_percentage, unique_title_words = find_common_title_words(videos_data)
            common_tags, tags_percentage, unique_tags = find_common_tags(videos_data)
            common_words, words_percentage, unique_desc_words = find_common_words(videos_data)
            
            # Store results in session state
            st.session_state.videos_data = videos_data
            st.session_state.common_title_words = common_title_words
            st.session_state.title_words_percentage = title_words_percentage
            st.session_state.unique_title_words = unique_title_words
            st.session_state.common_tags = common_tags
            st.session_state.tags_percentage = tags_percentage
            st.session_state.unique_tags = unique_tags
            st.session_state.common_words = common_words
            st.session_state.words_percentage = words_percentage
            st.session_state.unique_desc_words = unique_desc_words
            st.session_state.analysis_complete = True
    
    # Display analysis results if available
    if st.session_state.analysis_complete:
        # Get data from session state
        videos_data = st.session_state.videos_data
        common_title_words = st.session_state.common_title_words
        title_words_percentage = st.session_state.title_words_percentage
        unique_title_words = st.session_state.unique_title_words
        common_tags = st.session_state.common_tags
        tags_percentage = st.session_state.tags_percentage
        unique_tags = st.session_state.unique_tags
        common_words = st.session_state.common_words
        words_percentage = st.session_state.words_percentage
        unique_desc_words = st.session_state.unique_desc_words
        
        # Display results in scrollable tables
        st.subheader("Analysis Results")
        
        # Common words in titles section
        st.markdown("##### Common Words in Titles")
        if common_title_words:
            # Create a dataframe for common title words
            title_words_data = {
                "Word": [word for word, count, total in common_title_words],
                "Appears in": [f"{count} out of {total} videos" for word, count, total in common_title_words]
            }
            title_df = pd.DataFrame(title_words_data)
            st.dataframe(title_df, height=200)
        else:
            st.write("No common words found across the video titles.")
            
        # Non-overlapping words in titles section
        st.markdown("##### Non-overlapping Words in Titles")
        if unique_title_words:
            # Create a dataframe for unique title words
            unique_title_data = {
                "Word": list(unique_title_words.keys()),
                "Appears in": ["1 video" for _ in unique_title_words]
            }
            unique_title_df = pd.DataFrame(unique_title_data)
            st.dataframe(unique_title_df, height=200)
        else:
            st.write("No non-overlapping words found in the video titles.")
        
        # Common tags section
        st.markdown("##### Common Tags")
        if common_tags:
            # Create a dataframe for common tags
            tags_data = {
                "Tag": [tag for tag, count, total in common_tags],
                "Appears in": [f"{count} out of {total} videos" for tag, count, total in common_tags]
            }
            tags_df = pd.DataFrame(tags_data)
            st.dataframe(tags_df, height=200)
        else:
            st.write("No common tags found across the videos.")
            
        # Non-overlapping tags section
        st.markdown("##### Non-overlapping Tags")
        if unique_tags:
            # Create a dataframe for unique tags
            unique_tags_data = {
                "Tag": list(unique_tags.keys()),
                "Appears in": ["1 video" for _ in unique_tags]
            }
            unique_tags_df = pd.DataFrame(unique_tags_data)
            st.dataframe(unique_tags_df, height=200)
        else:
            st.write("No non-overlapping tags found across the videos.")
        
        # Common words in descriptions section
        st.markdown("##### Common Words in Descriptions")
        if common_words:
            # Create a dataframe for common description words
            words_data = {
                "Word": [word for word, count, total in common_words],
                "Appears in": [f"{count} out of {total} videos" for word, count, total in common_words]
            }
            words_df = pd.DataFrame(words_data)
            st.dataframe(words_df, height=200)
        else:
            st.write("No common words found across the video descriptions.")
            
        # Non-overlapping words in descriptions section
        st.markdown("##### Non-overlapping Words in Descriptions")
        if unique_desc_words:
            # Create a dataframe for unique description words
            unique_desc_data = {
                "Word": list(unique_desc_words.keys()),
                "Appears in": ["1 video" for _ in unique_desc_words]
            }
            unique_desc_df = pd.DataFrame(unique_desc_data)
            st.dataframe(unique_desc_df, height=200)
        else:
            st.write("No non-overlapping words found in the video descriptions.")
        
        # Add a clear divider between Analysis Results and Video Details
        st.divider()
        
        # Individual video details
        st.subheader("Video Details")
        
        # Add a download button for Excel file with recommendations
        excel_data = generate_excel_file(videos_data, common_title_words, common_tags, common_words,
                                       unique_title_words, unique_tags, unique_desc_words)
        
        # Use a key for the download button
        download_button_key = "download_excel_button"
        
        # Download button that doesn't reset the app state
        st.download_button(
            label="Download excel file with recommendations",
            data=excel_data,
            file_name="youtube_recommendations.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key=download_button_key,
            on_click=lambda: setattr(st.session_state, 'download_clicked', True)
        )
        
        # Show success message if download was clicked
        if st.session_state.download_clicked:
            st.success("Excel file downloaded successfully!")
        
        # Extract common elements for highlighting
        common_title_words_set = {word.lower() for word, _, _ in common_title_words}
        common_tags_set = {tag.lower() for tag, _, _ in common_tags}
        common_words_set = {word.lower() for word, _, _ in common_words}
        
        # Calculate match score for each video (for sorting)
        for video in videos_data:
            # Count matches in title
            title_matches = sum(1 for word in word_tokenize(video['title'].lower()) 
                              if word.isalpha() and word in common_title_words_set)
            
            # Count matches in tags
            tag_matches = sum(1 for tag in video['tags'] 
                            if tag.lower() in common_tags_set)
            
            # Count matches in description
            desc_words = [word for word in word_tokenize(video['description'].lower()) 
                        if word.isalpha() and word in common_words_set]
            desc_matches = len(set(desc_words))  # Count unique matches
            
            # Total match score
            video['match_score'] = title_matches + tag_matches + desc_matches
        
        # Sort videos by match score (highest to lowest)
        sorted_videos = sorted(videos_data, key=lambda x: x['match_score'], reverse=True)
        
        for video in sorted_videos:
            st.write("---")
            
            # Video title
            title_html = video['title']
            # Highlight common words in title while preserving original case
            for word in common_title_words_set:
                # Case-insensitive replacement with highlighting that preserves original case
                pattern = re.compile(re.escape(word), re.IGNORECASE)
                title_html = pattern.sub(lambda m: f'<span class="highlight">{m.group(0)}</span>', title_html)
            
            st.markdown(f"**Title:** {title_html}", unsafe_allow_html=True)
            
            # Display thumbnail with fixed width
            st.image(video['thumbnail'], width=426)
            
            # Publication date in human-readable format
            st.write(f"**Published:** {format_date(video['publication_date'])}")
            
            # Views
            st.write(f"**Views:** {video['views']:,}")
            
            # Tags with highlighting (collapsible)
            with st.expander("Show Tags"):
                if video['tags']:
                    # Create HTML for tags with highlighting that preserves original case
                    tags_html = []
                    for tag in video['tags']:
                        if tag.lower() in [t.lower() for t in common_tags_set]:
                            tags_html.append(f'<span class="highlight">{tag}</span>')
                        else:
                            tags_html.append(tag)
                    
                    st.markdown(", ".join(tags_html), unsafe_allow_html=True)
                else:
                    st.write("None")
            
            # Description (collapsible) with highlighting
            with st.expander("Show Description"):
                # Highlight common words in description while preserving original case
                desc_html = video['description']
                for word in common_words_set:
                    # Case-insensitive replacement with highlighting that preserves original case
                    pattern = re.compile(r'\b' + re.escape(word) + r'\b', re.IGNORECASE)
                    desc_html = pattern.sub(lambda m: f'<span class="highlight">{m.group(0)}</span>', desc_html)
                
                st.markdown(desc_html, unsafe_allow_html=True)

    # No need for closing div tag since we're not using a container div anymore

if __name__ == "__main__":
    main()
