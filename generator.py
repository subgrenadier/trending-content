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
        Creates an HTML file for the generated content inside a folder.
        """
        today = datetime.datetime.now().strftime('%Y-%m-%d')
        slug = keyword.lower().replace(' ', '-')

        # Frontmatter metadata (optional, can be removed if not needed)
        frontmatter = {
            'title': keyword,
            'date': today,
            'keywords': keyword,
            'description': f"Latest updates and insights about {keyword} in Malaysia",
            'slug': slug
        }

        # Define the post directory and file
        post_dir = Path(f'posts/{slug}')
        post_dir.mkdir(parents=True, exist_ok=True)  # Create folder for the post

        post_file = post_dir / 'index.html'  # Save as index.html inside the folder

        # HTML content with metadata
        post_content = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{keyword} - Trending Content</title>
            <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
        </head>
        <body class="bg-gray-100">
            <header class="bg-white shadow-md">
                <div class="container mx-auto px-4 py-6">
                    <h1 class="text-3xl font-bold text-gray-800">{keyword}</h1>
                </div>
            </header>

        <main class="container mx-auto px-4 py-8">
            <article class="bg-white rounded-lg shadow-md p-6">
                <h2 class="text-xl font-semibold mb-4">{keyword}</h2>
                <p class="text-gray-600 mb-4">{today}</p>
                <div class="prose">
                    {content}
                </div>
            </article>
        </main>
        </body>
        </html>
        """

        # Write the content to index.html
        post_file.write_text(post_content, encoding="utf-8")

        return post_file

    def generate_site(self):
        """
        Generates the static site using templates.
        """
        env = Environment(loader=FileSystemLoader('templates'))
        template = env.get_template('index.html')
        
        # Get all posts
        posts = []
        posts_dir = Path('posts')
        for post_file in posts_dir.glob('*.html'):
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