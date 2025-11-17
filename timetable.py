import requests
from bs4 import BeautifulSoup
from typing import Dict, List, Optional
import re
from urllib.parse import urljoin

# Base URL for the timetable website
BASE_URL = "https://data.guldu.uz/dars/"
AJAX_URL = urljoin(BASE_URL, "ajax.php")

def get_faculties() -> Dict[str, str]:
    """
    Fetches the list of faculties and their corresponding IDs from the main page.
    Returns a dictionary mapping faculty name to faculty ID.
    e.g. {'Axborot texnologiyalari va fizika-matematika fakulteti': '1'}
    """
    faculties = {}
    try:
        response = requests.get(BASE_URL)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")
        
        # Find all links that look like faculty links
        faculty_links = soup.select('div.col-md-4 a.btn, div.col-md-3 a.btn')
        
        for link in faculty_links:
            faculty_name = link.text.strip()
            href = link.get('href')
            if href and 'fak=' in href:
                # Extract the faculty ID from the href (e.g., "index.php?fak=1")
                match = re.search(r'fak=(\d+)', href)
                if match:
                    faculty_id = match.group(1)
                    faculties[faculty_name] = faculty_id
    except requests.RequestException as e:
        print(f"Error fetching faculties: {e}")
    return faculties

def get_groups_by_faculty(faculty_id: str) -> List[str]:
    """
    Fetches the list of group names for a given faculty ID.
    """
    groups = []
    faculty_url = urljoin(BASE_URL, f"index.php?fak={faculty_id}")
    try:
        response = requests.get(faculty_url)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")
        
        # Groups are in <h3> tags, e.g., <h3>911-21</h3>
        group_tags = soup.find_all('h3')
        for tag in group_tags:
            group_name = tag.text.strip()
            # Basic validation to ensure it looks like a group name
            if group_name and re.search(r'\d', group_name):
                groups.append(group_name)
    except requests.RequestException as e:
        print(f"Error fetching groups for faculty {faculty_id}: {e}")
    return sorted(groups)

def get_timetable(faculty_id: str, group: str) -> Dict[str, List[Dict[str, str]]]:
    """
    Fetches the weekly timetable for a specific group.
    Returns a dictionary where keys are days of the week in English.
    """
    timetable = {}
    days_map = {
        "Dushanba": "Monday", "Seshanba": "Tuesday", "Chorshanba": "Wednesday",
        "Payshanba": "Thursday", "Juma": "Friday", "Shanba": "Saturday"
    }
    try:
        payload = {'fak': faculty_id, 'q': group}
        response = requests.post(AJAX_URL, data=payload)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, "html.parser")
        
        rows = soup.find_all('tr')
        if not rows or len(rows) < 2:
            return {}

        # The actual day names are in the first row, second cell onwards
        header_cells = rows[0].find_all('th')
        # Mapping of table index to day name (e.g., {1: "Dushanba"})
        day_columns = {i: cell.text.strip() for i, cell in enumerate(header_cells) if cell.text.strip() in days_map}

        for row in rows[1:]:
            cells = row.find_all('td')
            if not cells or len(cells) <= 1:
                continue

            para_num = cells[0].text.strip()

            for i, day_name_uz in day_columns.items():
                if len(cells) > i:
                    cell = cells[i]
                    day_name_en = days_map[day_name_uz]

                    # Split lessons within a single cell by <hr> tag
                    lesson_parts_html = str(cell).split('<hr/>')

                    for part_html in lesson_parts_html:
                        part_soup = BeautifulSoup(part_html, 'html.parser')
                        
                        # Replace <br> with newlines for easier text extraction
                        for br in part_soup.find_all("br"):
                            br.replace_with("\n")
                        
                        lines = [line.strip() for line in part_soup.text.split('\n') if line.strip()]
                        
                        if not lines or "dars yo'q" in ' '.join(lines).lower():
                            continue

                        # Heuristics to find subject, lecturer, and room
                        subject = part_soup.find('b').text.strip() if part_soup.find('b') else lines[0]
                        room = next((line for line in lines if 'xona' in line.lower()), "N/A")
                        
                        # Assume lecturer is the line that is not the subject and not the room
                        lecturer = "N/A"
                        for line in lines:
                            if line != subject and line != room and not line.lower().startswith(('amaliyot', 'ma\'ruza', 'laboratoriya')):
                                lecturer = line
                                break
                        
                        if day_name_en not in timetable:
                            timetable[day_name_en] = []
                        
                        timetable[day_name_en].append({
                            "time": para_num,
                            "subject": subject,
                            "lecturer": lecturer,
                            "room": room,
                        })

    except requests.RequestException as e:
        print(f"Error fetching timetable for group {group}: {e}")
    except Exception as e:
        print(f"Error parsing timetable for group {group}: {e}")
        
    return timetable