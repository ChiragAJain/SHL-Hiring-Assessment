"""
SHL Assessment Scraper - Complete Implementation
Scrapes Individual Test Solutions from SHL Product Catalogue
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import json
import time
from typing import List, Dict

# Configuration
BASE_URL = "https://www.shl.com/products/product-catalog/?start={}&type=1"
TOTAL_PAGES = 32
ASSESSMENTS_PER_PAGE = 12


class SHLScraper:
    """Scraper for SHL Individual Test Solutions"""
    
    def __init__(self, headless: bool = False):
        """Initialize the scraper with Chrome driver"""
        options = webdriver.ChromeOptions()
        if headless:
            options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        
        self.driver = webdriver.Chrome(options=options)
        self.wait = WebDriverWait(self.driver, 10)
        self.assessments = []
    
    def scrape_assessment_detail(self, url: str) -> Dict:
        """Scrape detailed information from individual assessment page"""
        try:
            print(f"    Visiting: {url}")
            self.driver.get(url)
            time.sleep(2)
            
            assessment = {
                'url': url,
                'name': '',
                'adaptive_support': 'No',
                'description': '',
                'duration': '',
                'remote_support': 'No',
                'test_type': []
            }
            
            # Extract name
            try:
                name_elem = self.wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'h1, .product-title, .assessment-title'))
                )
                assessment['name'] = name_elem.text.strip()
            except:
                pass
            
            # Extract description
            try:
                desc_elem = self.driver.find_element(By.CSS_SELECTOR, '.product-description, .description, p.description')
                assessment['description'] = desc_elem.text.strip()
            except:
                try:
                    # Try alternative selector
                    desc_elem = self.driver.find_element(By.XPATH, "//div[contains(@class, 'description')]")
                    assessment['description'] = desc_elem.text.strip()
                except:
                    pass
            
            # Extract duration
            try:
                duration_elem = self.driver.find_element(By.XPATH, "//*[contains(text(), 'minute') or contains(text(), 'hour')]")
                assessment['duration'] = duration_elem.text.strip()
            except:
                pass
            
            # Check for adaptive support
            page_text = self.driver.page_source.lower()
            if 'adaptive' in page_text:
                assessment['adaptive_support'] = 'Yes'
            
            # Check for remote support
            if 'remote' in page_text or 'online' in page_text:
                assessment['remote_support'] = 'Yes'
            
            # Extract test types
            try:
                # Look for test type indicators
                test_type_mapping = {
                    'knowledge': 'Knowledge & Skills',
                    'skill': 'Knowledge & Skills',
                    'personality': 'Personality & Behaviour',
                    'behavior': 'Personality & Behaviour',
                    'behaviour': 'Personality & Behaviour',
                    'ability': 'Ability & Aptitude',
                    'aptitude': 'Ability & Aptitude',
                    'competenc': 'Competencies',
                    'situational': 'Biodata & Situational Judgement',
                    'biodata': 'Biodata & Situational Judgement',
                    'simulation': 'Simulations',
                    'development': 'Development & 360',
                    '360': 'Development & 360',
                    'exercise': 'Assessment Exercises'
                }
                
                page_text_lower = self.driver.page_source.lower()
                test_types_found = set()
                
                for keyword, test_type in test_type_mapping.items():
                    if keyword in page_text_lower:
                        test_types_found.add(test_type)
                
                assessment['test_type'] = list(test_types_found)
                
            except Exception as e:
                print(f"      Error extracting test types: {str(e)}")
            
            return assessment
            
        except Exception as e:
            print(f"      Error scraping detail page: {str(e)}")
            return None
    
    def scrape_catalogue_page(self, start: int) -> List[str]:
        """Scrape assessment URLs from a catalogue page"""
        url = BASE_URL.format(start)
        print(f"  Loading: {url}")
        
        try:
            self.driver.get(url)
            time.sleep(3)
            
            # Find all assessment links
            assessment_urls = []
            
            # Try multiple selectors
            selectors = [
                'a.product-link',
                'a[href*="/product-catalog/view/"]',
                '.product-item a',
                '.assessment-card a'
            ]
            
            for selector in selectors:
                try:
                    links = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if links:
                        for link in links:
                            href = link.get_attribute('href')
                            if href and '/view/' in href:
                                assessment_urls.append(href)
                        break
                except:
                    continue
            
            # Remove duplicates
            assessment_urls = list(set(assessment_urls))
            print(f"  Found {len(assessment_urls)} assessments")
            
            return assessment_urls
            
        except Exception as e:
            print(f"  Error loading page: {str(e)}")
            return []
    
    def scrape_all(self) -> List[Dict]:
        """Scrape all 32 pages of Individual Test Solutions"""
        print("="*60)
        print("SHL Assessment Scraper - Individual Test Solutions")
        print("="*60)
        print(f"Total pages to scrape: {TOTAL_PAGES}")
        print(f"Expected assessments: ~{TOTAL_PAGES * ASSESSMENTS_PER_PAGE}")
        print()
        
        for page in range(TOTAL_PAGES):
            start = page * ASSESSMENTS_PER_PAGE
            print(f"[Page {page + 1}/{TOTAL_PAGES}] Start index: {start}")
            
            # Get assessment URLs from catalogue page
            urls = self.scrape_catalogue_page(start)
            
            # Scrape each assessment detail page
            for i, url in enumerate(urls, 1):
                print(f"  [{i}/{len(urls)}] Scraping assessment...")
                assessment = self.scrape_assessment_detail(url)
                
                if assessment and assessment['name']:
                    self.assessments.append(assessment)
                    print(f"    ✓ {assessment['name']}")
                else:
                    print(f"    ✗ Failed to scrape")
                
                time.sleep(1)  # Rate limiting
            
            print()
            time.sleep(2)  # Delay between pages
        
        print("="*60)
        print(f"Scraping Complete!")
        print(f"Total assessments scraped: {len(self.assessments)}")
        print("="*60)
        
        return self.assessments
    
    def save_to_json(self, filename: str = 'shl_assessments.json'):
        """Save scraped assessments to JSON file"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.assessments, f, indent=2, ensure_ascii=False)
        print(f"\n✓ Saved {len(self.assessments)} assessments to {filename}")
    
    def close(self):
        """Close the browser"""
        self.driver.quit()


def main():
    """Main function"""
    print("\n" + "="*60)
    print("Starting SHL Assessment Scraper")
    print("="*60)
    print()
    print("Configuration:")
    print(f"  Base URL: {BASE_URL.format(0)}")
    print(f"  Total Pages: {TOTAL_PAGES}")
    print(f"  Assessments per page: {ASSESSMENTS_PER_PAGE}")
    print()
    print("This will take approximately 30-45 minutes...")
    print()
    
    input("Press Enter to start scraping...")
    
    # Create scraper
    scraper = SHLScraper(headless=False)
    
    try:
        # Scrape all assessments
        assessments = scraper.scrape_all()
        
        # Save to JSON
        if assessments:
            scraper.save_to_json('shl_assessments_new.json')
            
            print()
            print("="*60)
            print("Summary")
            print("="*60)
            print(f"Total assessments: {len(assessments)}")
            print()
            
            # Show statistics
            with_adaptive = sum(1 for a in assessments if a['adaptive_support'] == 'Yes')
            with_remote = sum(1 for a in assessments if a['remote_support'] == 'Yes')
            
            print(f"Adaptive support: {with_adaptive} ({with_adaptive/len(assessments)*100:.1f}%)")
            print(f"Remote support: {with_remote} ({with_remote/len(assessments)*100:.1f}%)")
            print()
            
            # Show sample
            if assessments:
                print("Sample assessment:")
                print(json.dumps(assessments[0], indent=2))
        else:
            print("\n✗ No assessments scraped")
    
    except KeyboardInterrupt:
        print("\n\nScraping interrupted by user")
        if scraper.assessments:
            print(f"Saving {len(scraper.assessments)} assessments scraped so far...")
            scraper.save_to_json('shl_assessments_partial.json')
    
    except Exception as e:
        print(f"\n✗ Error: {str(e)}")
        if scraper.assessments:
            print(f"Saving {len(scraper.assessments)} assessments scraped so far...")
            scraper.save_to_json('shl_assessments_partial.json')
    
    finally:
        scraper.close()


if __name__ == "__main__":
    main()
