import requests
from bs4 import BeautifulSoup
import openai
import datetime
import yaml
from pathlib import Path
import json
import g4f
import codecs
import chardet
from jinja2 import Environment, FileSystemLoader
from g4f.Provider import (
    Gemini
)

class TrendingContentGenerator:
    def __init__(self, openai_api_key):
        self.openai_api_key = openai_api_key
        openai.api_key = openai_api_key
    
    def safe_read_file(self, file_path):
        """
        Safely read a file by detecting its encoding first.
        Falls back to different encodings if UTF-8 fails.
        """
        # First, detect the file encoding
        with open(file_path, 'rb') as file:
            raw_data = file.read()
            detected = chardet.detect(raw_data)
            encoding = detected['encoding']
        
        # Try reading with detected encoding
        try:
            with codecs.open(file_path, 'r', encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            # Fallback encodings to try
            fallback_encodings = ['utf-8', 'cp1252', 'iso-8859-1', 'ascii']
            for enc in fallback_encodings:
                try:
                    with codecs.open(file_path, 'r', encoding=enc) as f:
                        return f.read()
                except UnicodeDecodeError:
                    continue
            # If all encodings fail, raise an error
            raise ValueError(f"Could not read file {file_path} with any supported encoding")
        
    def get_trending_keywords(self):
        """
        Fetches trending topics from Google Trends Malaysia.
        Returns a list of trending keywords.
        """
        # Using Google Trends API for Malaysia
        trends_url = "https://trends.google.com/trends/api/dailytrends"
        params = {
            "hl": "en-MY",
            "tz": "480",  # UTC+8 for Malaysia
            "geo": "MY",
            "ns": "15"
        }
        
        try:
            response = requests.get(trends_url, params=params)
            # Remove ")]}'" from the beginning of the response
            clean_data = response.text[5:]
            data = json.loads(clean_data)
            
            trends = []
            for topic in data['default']['trendingSearchesDays'][0]['trendingSearches']:
                trends.append(topic['title']['query'])
            print(f"Top 5 trending topics in Malaysia: {trends[:5]}")
            return trends[:5]  # Return top 5 trending topics
        except Exception as e:
            print(f"Error fetching trends: {e}")
            return ["Malaysia technology", "Malaysia business", "Malaysia tourism"]  # Fallback keywords
        
    def generate_article(self, keyword):
        """
        Generates an article based on the given keyword using OpenAI's API.
        """
        prompt = f"""Write a comprehensive, engaging article about {keyword} 
        specifically for a Malaysian audience. Include relevant local context and perspectives.
        The article should be around 800 words with proper headings and paragraphs."""
        
        try:
            response = g4f.ChatCompletion.create(
                # model="gpt-3.5-turbo",
                # model = "gpt-4-turbo",
                # model=client.models.gpt_4,
                model="gemini",
                provider=Gemini,
                # provider="g4f.Provider.Gemini",
                # model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a professional content writer familiar with Malaysian culture and context."},
                    {"role": "user", "content": prompt}
                ]
            )
            return response
        except Exception as e:
            print(f"Error generating article: {e}")
            return f"Error generating article for keyword: {keyword}"

    def create_post(self, keyword, content):
        """
        Creates a markdown file with YAML frontmatter for the generated content.
        """
        today = datetime.datetime.now().strftime('%Y-%m-%d')
        slug = keyword.lower().replace(' ', '-')
        
        frontmatter = {
            'title': keyword,
            'date': today,
            'keywords': keyword,
            'description': f"Latest updates and insights about {keyword} in Malaysia",
            'slug': slug
        }
        
        post_content = f"""---
{yaml.dump(frontmatter)}---

{content}
"""
        
        # Save to _posts directory
        posts_dir = Path('_posts')
        posts_dir.mkdir(exist_ok=True)
        
        post_file = posts_dir / f"{today}-{slug}.md"
        post_file.write_text(post_content)
        
        return post_file

    def generate_site(self):
        """
        Generates the static site using templates.
        """
        env = Environment(loader=FileSystemLoader('templates'))
        template = env.get_template('index.html')
        
        # Get all posts
        posts = []
        posts_dir = Path('_posts')
        for post_file in posts_dir.glob('*.md'):
            try:
                content = self.safe_read_file(post_file)
                # Parse frontmatter and content
                _, fm, content = content.split('---', 2)
                metadata = yaml.safe_load(fm)
                posts.append({
                    'metadata': metadata,
                    'content': content.strip()
                })
            except Exception as e:
                print(f"Error processing file {post_file}: {e}")
                continue
        
        # Sort posts by date
        posts.sort(key=lambda x: x['metadata']['date'], reverse=True)
        
        # Generate index.html
        output = template.render(posts=posts)
        with codecs.open('index.html', 'w', 'ascii', errors='ignore') as f:
            f.write(output)

def main():
    # Initialize with your OpenAI API key
    generator = TrendingContentGenerator('your-openai-api-key')
    
    # Get trending keywords
    keywords = generator.get_trending_keywords()
    
    # Generate content for each keyword
    for keyword in keywords:
        content = generator.generate_article(keyword)
        generator.create_post(keyword, content)
    
    # Generate the static site
    generator.generate_site()

if __name__ == "__main__":
    main()