from flask import Flask, render_template, request, flash, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import re
import yaml
import os
from pathlib import Path

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///department.db'
db = SQLAlchemy(app)

# Models
class Faculty(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    specialization = db.Column(db.String(200))
    
class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    credits = db.Column(db.Integer, nullable=False)

# Context processor for current year
@app.context_processor
def inject_year():
    return {'year': datetime.now().year}

# Routes
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/faculty')
def faculty():
    faculty_members = Faculty.query.all()
    return render_template('faculty.html', faculty=faculty_members)

@app.route('/courses')
def courses():
    courses_list = Course.query.all()
    return render_template('courses.html', courses=courses_list)

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/course-viewer')
def course_viewer_page():
    # Get the course parameter from the query string
    course_slug = request.args.get('course', '')
    
    # Map course slugs to IDs
    course_slug_map = {
        'web-development': '1',
        'software-development': '2',
        'database-development': '3'
    }
    
    # Redirect to the proper course endpoint if a valid course is provided
    if course_slug in course_slug_map:
        return redirect(url_for('view_course', course_id=course_slug_map[course_slug]))
    
    # Otherwise, show the empty course viewer
    return render_template('course_viewer.html', course_data=None, course_id=None)

@app.route('/resources')
def resources():
    return render_template('resources.html')

@app.route('/terms')
def terms():
    return render_template('terms.html')

@app.route('/privacy')
def privacy():
    return render_template('privacy.html')

def parse_mdx_file(file_path):
    """Parse an MDX file and return the content as a structured dictionary"""
    print(f"Parsing MDX file: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Extract the YAML front matter
    front_matter_match = re.match(r'^---\n(.*?)\n---\n', content, re.DOTALL)
    
    if front_matter_match:
        # Parse the YAML front matter
        front_matter = yaml.safe_load(front_matter_match.group(1))
        # Get the content after the front matter
        main_content = content[front_matter_match.end():]
    else:
        front_matter = {}
        main_content = content
    
    print(f"Front matter: {front_matter}")
    
    # Parse the sections - simplified approach
    course_data = {**front_matter, 'sections': []}
    
    # Split content by section headers (## headings)
    sections = re.split(r'(?=^## )', main_content, flags=re.MULTILINE)
    
    for section_content in sections:
        if not section_content.strip():
            continue
            
        # Skip sections header if present
        if section_content.strip().startswith('# Sections'):
            continue
            
        # Extract section title and ID
        section_title_match = re.search(r'^## .+?\n\n- title: "(.+?)"\n- id: "(.+?)"', section_content, re.DOTALL)
        if not section_title_match:
            continue
            
        section_title = section_title_match.group(1)
        section_id = section_title_match.group(2)
        
        section = {
            'id': section_id,
            'title': section_title,
            'completed': False,
            'pages': []
        }
        
        # Find all pages within this section
        page_blocks = re.findall(r'#### (.+?)\n\n- id: "(.+?)"\n- content: \|(.*?)(?=^####|\Z)', 
                               section_content, re.DOTALL | re.MULTILINE)
        
        for page_title, page_id, page_content in page_blocks:
            # Clean up the content
            content_lines = [line.strip() for line in page_content.split('\n')]
            markdown_content = '\n'.join(content_lines)
            
            page = {
                'id': page_id,
                'title': page_title.strip(),
                'completed': False,
                'content': f"""
                    <div class="section-content">
                        {markdown_content}
                        
                        <div class="complete-section">
                            <button onclick="markPageComplete('{section_id}', '{page_id}')" class="complete-button">
                                Mark Complete <i class="fas fa-check"></i>
                            </button>
                        </div>
                    </div>
                """
            }
            
            section['pages'].append(page)
        
        if section['pages']:
            course_data['sections'].append(section)
    
    print(f"Parsed {len(course_data['sections'])} sections with titles: {[s['title'] for s in course_data['sections']]}")
    
    return course_data

@app.route('/course/<course_id>')
def view_course(course_id):
    # Map course IDs to the corresponding MDX files in templates/data directory
    course_file_map = {
        '1': 'templates/data/webDesign&Dev.mdx',
        '2': 'templates/data/softwareDesign&Dev.mdx',
        '3': 'templates/data/databaseDesign&Dev.mdx',
    }
    
    if course_id not in course_file_map:
        flash(f"Course with ID {course_id} not found", "error")
        return redirect(url_for('courses'))
    
    # Get the file path for the requested course
    file_path = course_file_map.get(course_id)
    
    # Parse the MDX file to get the course data
    course_data = parse_mdx_file(file_path)
    
    return render_template('course_viewer.html', course_data=course_data, course_id=course_id)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True) 