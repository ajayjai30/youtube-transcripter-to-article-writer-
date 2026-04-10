import re
import io
import streamlit as st
from youtube_transcript_api import YouTubeTranscriptApi
from google import genai
from fpdf import FPDF

# --- Configuration ---
GEMINI_API_KEY = "AIzaSyCoiA8CBulrS6_Ye3CQ1iP6Ncaao4eDI9Q"

# --- UI Setup ---
st.set_page_config(page_title="YouTube to PDF Writer", page_icon="📝", layout="centered")

st.title("🎥 YouTube to Insightful PDF")
st.markdown("Turn any YouTube video into a beautifully formatted, AI-written PDF article.")

# --- Sidebar / Inputs ---
with st.sidebar:
    st.header("Configuration")
    st.markdown("### How it works")
    st.markdown("1. Scrapes the YouTube Transcript\n2. AI writes a structured article\n3. Converts the text directly to a simple PDF using fpdf2.")
    st.success("API Key is securely loaded internally.")

youtube_url = st.text_input("YouTube Video URL", placeholder="https://www.youtube.com/watch?v=...")

# --- Helper Functions ---
def extract_video_id(url):
    match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", url)
    return match.group(1) if match else None

def get_transcript(video_id):
    ytt_api = YouTubeTranscriptApi()
    fetched_transcript = ytt_api.fetch(video_id)
    return " ".join([snippet.text for snippet in fetched_transcript])

def generate_article(transcript_text, api_key):
    client = genai.Client(api_key=api_key)
    prompt = f"""
    You are an expert tech journalist. Take this YouTube transcript and turn it into a highly engaging, structured article.
    Format your response cleanly using only standard text. 
    Use the exact string "TITLE:" before the main title.
    Use the exact string "HEADING:" before any section headers.
    Do not use bolding or italic markdown (like ** or *).
    
    Transcript: {transcript_text}
    """
    
    response = client.models.generate_content(
        model='gemini-3-flash-preview',
        contents=prompt,
    )
    return response.text

# --- Custom FPDF Class for Styling ---
class ArticlePDF(FPDF):
    def header(self):
        pass

    def footer(self):
        self.set_y(-15)
        self.set_font('helvetica', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', align='C')

    def chapter_title(self, title):
        self.set_font('helvetica', 'B', 20)
        self.set_text_color(44, 62, 80)
        self.multi_cell(0, 10, title)
        self.ln(10)

    def chapter_heading(self, heading):
        self.set_font('helvetica', 'B', 14)
        self.set_text_color(41, 128, 185)
        self.ln(5)
        self.multi_cell(0, 8, heading)
        self.ln(2)

    def chapter_body(self, body):
        self.set_font('helvetica', '', 11)
        self.set_text_color(51, 51, 51)
        clean_body = body.replace('’', "'").replace('“', '"').replace('”', '"')
        self.multi_cell(0, 6, clean_body)
        self.ln()

def create_pdf_bytes(article_text):
    pdf = ArticlePDF()
    pdf.add_page()
    
    lines = article_text.split('\n')
    current_body = []
    
    for line in lines:
        line = line.strip()
        if not line:
            current_body.append("\n") 
            continue
            
        if line.startswith("TITLE:"):
            if current_body:
                pdf.chapter_body(" ".join(current_body))
                current_body = []
            title_text = line.replace("TITLE:", "").strip()
            pdf.chapter_title(title_text)
            
        elif line.startswith("HEADING:"):
            if current_body:
                pdf.chapter_body(" ".join(current_body))
                current_body = []
            heading_text = line.replace("HEADING:", "").strip()
            pdf.chapter_heading(heading_text)
            
        else:
            current_body.append(line)
            
    if current_body:
         pdf.chapter_body(" ".join(current_body))
         
    pdf_buffer = io.BytesIO()
    pdf_bytes = pdf.output(dest='S')
    pdf_buffer.write(pdf_bytes)
    return pdf_buffer.getvalue()

# --- Main Execution Flow ---
if st.button("Generate PDF Document", type="primary"):
    if not youtube_url:
        st.error("⚠️ Please enter a valid YouTube URL.")
    else:
        video_id = extract_video_id(youtube_url)
        
        if not video_id:
            st.error("⚠️ Could not extract a valid YouTube Video ID from the URL.")
        else:
            try:
                with st.spinner("Step 1/3: Fetching video transcript..."):
                    raw_transcript = get_transcript(video_id)
                
                with st.spinner("Step 2/3: AI is writing the article..."):
                    article_text = generate_article(raw_transcript, GEMINI_API_KEY)
                
                with st.spinner("Step 3/3: Formatting simple PDF document..."):
                    pdf_data = create_pdf_bytes(article_text)
                
                st.success("🎉 Document generated successfully!")
                
                st.download_button(
                    label="⬇️ Download PDF Article",
                    data=pdf_data,
                    file_name=f"YouTube_Insight_{video_id}.pdf",
                    mime="application/pdf"
                )
                
                with st.expander("Preview Article Content"):
                    st.text(article_text)

            except Exception as e:
                st.error(f"An error occurred: {str(e)}")