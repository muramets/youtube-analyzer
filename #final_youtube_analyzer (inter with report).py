import streamlit as st
import re
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

# Apply more aggressive CSS to force fixed width and centered layout
st.markdown("""
<style>
    /* Global settings to prevent horizontal scrollbar */
    body {
        overflow-x: hidden !important;
    }
    
    /* Main container styling */
    .main .block-container {
        max-width: 1000px !important;
        padding-top: 2rem !important;
        padding-right: 2rem !important;
        padding-left: 2rem !important;
        padding-bottom: 2rem !important;
        margin: 0 auto !important;
        overflow-x: hidden !important;
    }
    
    /* App container styling - updated for Streamlit 1.44+ */
    div[data-testid="stAppViewContainer"] {
        width: 100% !important;
        overflow-x: hidden !important;
    }
    
    /* Center content with fixed width */
    div[data-testid="stAppViewContainer"] > section,
    div[data-testid="stAppViewContainer"] > div,
    div[data-testid="stAppViewContainer"] > section > div,
    div[data-testid="stAppViewContainer"] > section > div > div {
        max-width: 1000px !important;
        margin-left: auto !important;
        margin-right: auto !important;
        padding-left: 0 !important;
        padding-right: 0 !important;
        overflow-x: hidden !important;
    }
    
    /* Ensure horizontal blocks don't cause overflow */
    div[data-testid="stHorizontalBlock"],
    div[data-testid="stVerticalBlock"] {
        width: 100% !important;
        max-width: 1000px !important;
        margin-left: auto !important;
        margin-right: auto !important;
        padding-left: 0 !important;
        padding-right: 0 !important;
        overflow-x: hidden !important;
    }
    
    /* Unified background color for the entire app */
    .stApp, .main .block-container {
        background-color: #121212 !important;
    }
    
    /* Ensure vertical scrollbar appears at the edge of the screen */
    .stApp {
        overflow-y: auto !important;
        overflow-x: hidden !important;
    }
    
    /* Image styling */
    .stImage img {
        display: block !important;
        margin: 0 !important;
    }
    
    /* Center title only */
    h1 {
        text-align: center !important;
    }
    
    /* Left-align other text elements */
    .stMarkdown, .stText, h2, h3, h4, h5, h6, p {
        text-align: left !important;
    }
    
    /* Add spacing between sections */
    .section-divider {
        margin-top: 2rem !important;
        margin-bottom: 2rem !important;
    }
    
    /* Highlight matching elements with text color instead of background */
    .highlight {
        color: #008000 !important;
        font-weight: 500 !important;
    }
    
    /* Make sure input fields don't stretch */
    .stTextInput, .stButton {
        width: 100% !important;
        max-width: 100% !important;
    }
    
    /* Custom styling for clickable images */
    .clickable-image {
        cursor: pointer !important;
        transition: transform 0.3s ease !important;
    }
    
    .clickable-image:hover {
        transform: scale(1.02) !important;
    }
</style>
""", unsafe_allow_html=True)
# YouTube API Key - Replace with your actual API key
YOUTUBE_API_KEY = "AIzaSyDCRnjNNuvzmp45rYZiGae7q6RggG4d3NI"

# Initialize YouTube API client
def get_youtube_client():
    return build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)

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

# Find common tags across videos
def find_common_tags(videos_data):
    if not videos_data:
        return [], 0
    
    # Collect all unique tags across all videos
    all_tags = set()
    for video in videos_data:
        all_tags.update(video['tags'])
    
    # Find common tags (intersection of all videos' tags)
    common_tags = set(videos_data[0]['tags']) if videos_data else set()
    for video in videos_data[1:]:
        common_tags = common_tags.intersection(set(video['tags']))
    
    # Calculate percentage of common tags out of all unique tags
    result = []
    overall_percentage = 0
    
    if all_tags:
        overall_percentage = (len(common_tags) / len(all_tags)) * 100
        
        # Create result list with individual tag info
        for tag in common_tags:
            result.append((tag, overall_percentage))
    
    return result, overall_percentage

# Download all required NLTK resources
def download_nltk_resources():
    resources = ['punkt', 'stopwords', 'punkt_tab']
    for resource in resources:
        try:
            nltk.data.find(f'tokenizers/{resource}')
        except LookupError:
            nltk.download(resource)

# Find common words in descriptions
def find_common_words(videos_data, min_frequency=2):
    if not videos_data:
        return [], 0
    
    # Download NLTK resources if not already downloaded
    download_nltk_resources()
    
    # Process descriptions
    all_descriptions = [video['description'] for video in videos_data]
    
    # Tokenize and clean words
    all_words_lists = []
    all_unique_words = set()
    stop_words = set(stopwords.words('english') + stopwords.words('russian'))
    
    for description in all_descriptions:
        # Tokenize
        words = word_tokenize(description.lower())
        
        # Filter out stopwords, punctuation, and short words
        filtered_words = [
            word for word in words 
            if word.isalpha() and word not in stop_words and len(word) > 2
        ]
        
        all_words_lists.append(set(filtered_words))
        all_unique_words.update(filtered_words)
    
    # Find words that appear in all descriptions
    result = []
    overall_percentage = 0
    
    if all_words_lists:
        common_words = set.intersection(*all_words_lists) if all_words_lists else set()
        
        # Calculate percentage of common words out of all unique words
        if all_unique_words:
            overall_percentage = (len(common_words) / len(all_unique_words)) * 100
            
            # Create result list with individual word info
            for word in common_words:
                result.append((word, overall_percentage))
    
    return result, overall_percentage

# Find common words in titles
def find_common_title_words(videos_data):
    if not videos_data:
        return [], 0
    
    # Download NLTK resources if not already downloaded
    download_nltk_resources()
    
    # Process titles
    all_titles = [video['title'] for video in videos_data]
    
    # Tokenize and clean words
    all_words_lists = []
    all_unique_words = set()
    stop_words = set(stopwords.words('english') + stopwords.words('russian'))
    
    for title in all_titles:
        # Tokenize
        words = word_tokenize(title.lower())
        
        # Filter out stopwords, punctuation, and short words
        filtered_words = [
            word for word in words 
            if word.isalpha() and word not in stop_words and len(word) > 2
        ]
        
        all_words_lists.append(set(filtered_words))
        all_unique_words.update(filtered_words)
    
    # Find words that appear in all titles
    result = []
    overall_percentage = 0
    
    if all_words_lists:
        common_words = set.intersection(*all_words_lists) if all_words_lists else set()
        
        # Calculate percentage of common words out of all unique words
        if all_unique_words:
            overall_percentage = (len(common_words) / len(all_unique_words)) * 100
            
            # Create result list with individual word info
            for word in common_words:
                result.append((word, overall_percentage))
    
    return result, overall_percentage

# Function to generate Excel file with recommendations
def generate_excel_file(videos_data, common_title_words, common_tags, common_words):
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
        title_words_data = [{'Common Title Words': word} for word, _ in common_title_words] if common_title_words else []
        
        # Common tags
        tags_data = [{'Common Tags': tag} for tag, _ in common_tags] if common_tags else []
        
        # Common description words
        words_data = [{'Common Description Words': word} for word, _ in common_words] if common_words else []
        
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
            common_title_words, title_words_percentage = find_common_title_words(videos_data)
            common_tags, tags_percentage = find_common_tags(videos_data)
            common_words, words_percentage = find_common_words(videos_data)
            
            # Store results in session state
            st.session_state.videos_data = videos_data
            st.session_state.common_title_words = common_title_words
            st.session_state.title_words_percentage = title_words_percentage
            st.session_state.common_tags = common_tags
            st.session_state.tags_percentage = tags_percentage
            st.session_state.common_words = common_words
            st.session_state.words_percentage = words_percentage
            st.session_state.analysis_complete = True
    
    # Display analysis results if available
    if st.session_state.analysis_complete:
        # Get data from session state
        videos_data = st.session_state.videos_data
        common_title_words = st.session_state.common_title_words
        title_words_percentage = st.session_state.title_words_percentage
        common_tags = st.session_state.common_tags
        tags_percentage = st.session_state.tags_percentage
        common_words = st.session_state.common_words
        words_percentage = st.session_state.words_percentage
        
        # Display results
        st.subheader("Analysis Results")
        
        # Common words in titles section
        st.markdown(f"##### Common Words in Titles ({title_words_percentage:.0f}%)")
        if common_title_words:
            st.write(", ".join([word for word, _ in common_title_words]))
        else:
            st.write("No common words found across the video titles.")
        
        # Common tags section
        st.markdown(f"##### Common Tags ({tags_percentage:.0f}%)")
        if common_tags:
            st.write(", ".join([tag for tag, _ in common_tags]))
        else:
            st.write("No common tags found across the videos.")
        
        # Common words in descriptions section
        st.markdown(f"##### Common Words in Descriptions ({words_percentage:.0f}%)")
        if common_words:
            st.write(", ".join([word for word, _ in common_words]))
        else:
            st.write("No common words found across the video descriptions.")
        
        # Add a clear divider between Analysis Results and Video Details
        st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)
        
        # Individual video details
        st.subheader("Video Details")
        
        # Add a download button for Excel file with recommendations
        excel_data = generate_excel_file(videos_data, common_title_words, common_tags, common_words)
        
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
        common_title_words_set = {word for word, _ in common_title_words}
        common_tags_set = {tag for tag, _ in common_tags}
        common_words_set = {word for word, _ in common_words}
        
        for video in videos_data:
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
            
            # Tags with highlighting
            if video['tags']:
                st.write("**Tags:**")
                
                # Create HTML for tags with highlighting that preserves original case
                tags_html = []
                for tag in video['tags']:
                    if tag.lower() in [t.lower() for t in common_tags_set]:
                        tags_html.append(f'<span class="highlight">{tag}</span>')
                    else:
                        tags_html.append(tag)
                
                st.markdown(", ".join(tags_html), unsafe_allow_html=True)
            else:
                st.write("**Tags:** None")
            
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
