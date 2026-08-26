import hashlib
import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

class DocumentExtractor:
    """Handles extraction and storage of Google Doc content with metadata and hash tracking."""
    
    def __init__(self, storage_dir: str = "document_store"):
        self.storage_dir = storage_dir
        self.docs_service = None
        self.drive_service = None
        self._initialize_services()
        self._ensure_storage_dir()
        
    def _initialize_services(self):
        """Initialize Google API services."""
        SCOPES = [
            'https://www.googleapis.com/auth/documents.readonly',
            'https://www.googleapis.com/auth/drive.readonly'
        ]
        try:
            creds = Credentials.from_authorized_user_file('token.json', SCOPES)
            self.docs_service = build('docs', 'v1', credentials=creds)
            self.drive_service = build('drive', 'v3', credentials=creds)
        except Exception as e:
            print(f"Error initializing services: {e}")
            raise
    
    def _ensure_storage_dir(self):
        """Create storage directory structure if it doesn't exist."""
        os.makedirs(self.storage_dir, exist_ok=True)
        os.makedirs(os.path.join(self.storage_dir, 'raw'), exist_ok=True)
        os.makedirs(os.path.join(self.storage_dir, 'metadata'), exist_ok=True)
        os.makedirs(os.path.join(self.storage_dir, 'processed'), exist_ok=True)
    
    def list_google_docs(self, limit: int = 20) -> List[Dict]:
        """List all Google Docs available."""
        try:
            results = self.drive_service.files().list(
                q="mimeType='application/vnd.google-apps.document' and trashed=false",
                fields="files(id, name, createdTime, modifiedTime, owners)",
                orderBy="modifiedTime desc",
                pageSize=limit
            ).execute()
            return results.get('files', [])
        except HttpError as e:
            print(f"Error listing docs: {e}")
            return []
    
    def _extract_text_from_elements(self, elements: List[Dict]) -> str:
        """Recursively extract plain text from document elements."""
        text = ''
        for element in elements:
            if 'paragraph' in element:
                for para_element in element['paragraph']['elements']:
                    if 'textRun' in para_element:
                        text += para_element['textRun'].get('content', '')
            elif 'table' in element:
                for row in element['table'].get('tableRows', []):
                    for cell in row.get('tableCells', []):
                        text += self._extract_text_from_elements(cell.get('content', []))
                        text += '\t'
                text += '\n'
            elif 'sectionBreak' in element:
                text += '\n\n'
            elif 'horizontalRule' in element:
                text += '\n' + '-'*80 + '\n'
        return text
    
    def _extract_structured_elements(self, elements: List[Dict]) -> List[Dict]:
        """Extract content with structural metadata."""
        structured = []
        for element in elements:
            if 'paragraph' in element:
                para_data = {
                    'type': 'paragraph',
                    'elements': []
                }
                for para_element in element['paragraph']['elements']:
                    if 'textRun' in para_element:
                        text_run = para_element['textRun']
                        para_data['elements'].append({
                            'type': 'text_run',
                            'content': text_run.get('content', ''),
                            'style': text_run.get('textStyle', {})
                        })
                    elif 'autoText' in para_element:
                        para_data['elements'].append({
                            'type': 'auto_text',
                            'content': para_element['autoText'].get('content', '')
                        })
                    elif 'equation' in para_element:
                        para_data['elements'].append({
                            'type': 'equation',
                            'content': 'Equation found'
                        })
                structured.append(para_data)
                
            elif 'table' in element:
                table_data = {
                    'type': 'table',
                    'rows': []
                }
                for row in element['table'].get('tableRows', []):
                    row_data = []
                    for cell in row.get('tableCells', []):
                        cell_content = self._extract_structured_elements(cell.get('content', []))
                        row_data.append(cell_content)
                    table_data['rows'].append(row_data)
                structured.append(table_data)
                
            elif 'sectionBreak' in element:
                structured.append({
                    'type': 'section_break'
                })
                
        return structured
    
    def _get_document_metadata(self, doc_id: str) -> Dict:
        """Fetch document metadata from Drive API."""
        try:
            file_metadata = self.drive_service.files().get(
                fileId=doc_id,
                fields='id,name,mimeType,createdTime,modifiedTime,owners,size,version'
            ).execute()
            
            return {
                'id': file_metadata.get('id'),
                'name': file_metadata.get('name'),
                'mime_type': file_metadata.get('mimeType'),
                'created_time': file_metadata.get('createdTime'),
                'modified_time': file_metadata.get('modifiedTime'),
                'owners': [owner.get('emailAddress', 'Unknown') for owner in file_metadata.get('owners', [])],
                'size': file_metadata.get('size', 0),
                'version': file_metadata.get('version', 1)
            }
        except HttpError as e:
            print(f"Error fetching metadata: {e}")
            return {'id': doc_id, 'error': str(e)}
    
    def _calculate_hash(self, content: str) -> str:
        """Calculate SHA-256 hash of content."""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def _get_stored_version(self, doc_id: str) -> Optional[Dict]:
        """Check if we have a stored version of this document."""
        metadata_path = os.path.join(self.storage_dir, 'metadata', f'{doc_id}.json')
        if os.path.exists(metadata_path):
            with open(metadata_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None
    
    def extract_document(self, doc_id: str, force_extract: bool = False) -> Dict[str, Any]:
        """
        Extract document content with metadata and track changes.
        
        Returns:
            Dict with keys: document_id, metadata, content, structured_content, 
                          hash, changed, previous_hash
        """
        print(f"\n📄 Extracting document: {doc_id}")
        
        # 1. Fetch document
        try:
            document = self.docs_service.documents().get(
                documentId=doc_id,
                includeTabsContent=True
            ).execute()
        except HttpError as e:
            print(f"Error fetching document: {e}")
            return {'error': str(e)}
        
        # 2. Get metadata from Drive
        drive_metadata = self._get_document_metadata(doc_id)
        print(f"   Title: {drive_metadata.get('name', 'Unknown')}")
        print(f"   Modified: {drive_metadata.get('modified_time', 'Unknown')}")
        
        # 3. Extract content
        full_text = ""
        structured_content = {
            'tabs': []
        }
        tab_info = []
        
        # Handle single vs multiple tabs
        tabs = document.get('tabs', [{'documentTab': {'title': 'Main', 'body': document.get('body', {})}}])
        
        for idx, tab in enumerate(tabs):
            tab_title = tab.get('documentTab', {}).get('title', f'Tab_{idx+1}')
            tab_body = tab.get('documentTab', {}).get('body', {})
            tab_content = tab_body.get('content', [])
            
            # Extract both plain text and structured
            tab_text = self._extract_text_from_elements(tab_content)
            tab_structured = self._extract_structured_elements(tab_content)
            
            full_text += f"\n\n=== {tab_title} ===\n\n{tab_text}"
            
            tab_info.append({
                'title': tab_title,
                'text': tab_text,
                'structured': tab_structured,
                'character_count': len(tab_text)
            })
            
            structured_content['tabs'] = tab_info
        
        # 4. Calculate hash
        content_hash = self._calculate_hash(full_text)
        print(f"   Hash: {content_hash[:16]}...")
        
        # 5. Check for changes
        stored_data = self._get_stored_version(doc_id)
        changed = False
        previous_hash = None
        
        if stored_data:
            previous_hash = stored_data.get('current_hash')
            if previous_hash != content_hash:
                changed = True
                print(f"   ⚠️  Document CHANGED!")
                print(f"      Previous: {previous_hash[:16]}...")
                print(f"      New:      {content_hash[:16]}...")
            else:
                print(f"   ✅ Document unchanged (hash matches)")
        else:
            print(f"   📝 New document detected")
        
        # 6. Prepare result
        result = {
            'document_id': doc_id,
            'metadata': {
                **drive_metadata,
                'extraction_timestamp': datetime.utcnow().isoformat() + 'Z',
                'tab_count': len(tabs)
            },
            'content': full_text,
            'structured_content': structured_content,
            'hash': content_hash,
            'changed': changed,
            'previous_hash': previous_hash,
            'tabs_metadata': tab_info
        }
        
        # 7. Store the result
        if force_extract or changed or not stored_data:
            self._store_document(result)
            print(f"   💾 Document stored successfully")
        else:
            print(f"   ⏭️  Skipping storage - document unchanged")
        
        return result
    
    def _store_document(self, doc_data: Dict[str, Any]):
        """Store document data in the storage system."""
        doc_id = doc_data['document_id']
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        
        # Create versioned directory
        version_dir = os.path.join(self.storage_dir, 'raw', doc_id)
        os.makedirs(version_dir, exist_ok=True)
        
        # 1. Store raw content with version
        version_file = os.path.join(version_dir, f'v_{timestamp}.txt')
        with open(version_file, 'w', encoding='utf-8') as f:
            f.write(doc_data['content'])
        
        # 2. Store structured JSON
        structured_file = os.path.join(version_dir, f'v_{timestamp}_structured.json')
        with open(structured_file, 'w', encoding='utf-8') as f:
            store_data = {**doc_data}
            store_data['content'] = f"See {version_file}"
            json.dump(store_data, f, indent=2, ensure_ascii=False)
        
        # 3. Update main metadata file
        metadata_path = os.path.join(self.storage_dir, 'metadata', f'{doc_id}.json')
        if os.path.exists(metadata_path):
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            if 'versions' not in metadata:
                metadata['versions'] = []
            metadata['versions'].append({
                'timestamp': timestamp,
                'hash': doc_data['hash'],
                'version_file': version_file
            })
        else:
            metadata = {
                'document_id': doc_id,
                'first_extracted': timestamp,
                'versions': []
            }
        
        metadata['last_modified'] = timestamp
        metadata['current_hash'] = doc_data['hash']
        metadata['tab_count'] = doc_data['metadata'].get('tab_count', 1)
        metadata['document_name'] = doc_data['metadata'].get('name', 'Unknown')
        
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        # 4. Save to processed directory for RAG pipeline
        processed_data = {
            'document_id': doc_id,
            'hash': doc_data['hash'],
            'content': doc_data['content'],
            'metadata': doc_data['metadata'],
            'tabs_metadata': doc_data['tabs_metadata']
        }
        processed_path = os.path.join(self.storage_dir, 'processed', f'{doc_id}_{timestamp}.json')
        with open(processed_path, 'w', encoding='utf-8') as f:
            json.dump(processed_data, f, indent=2, ensure_ascii=False)
    
    def list_stored_documents(self) -> List[Dict]:
        """List all stored documents with their metadata."""
        metadata_dir = os.path.join(self.storage_dir, 'metadata')
        documents = []
        
        if os.path.exists(metadata_dir):
            for filename in os.listdir(metadata_dir):
                if filename.endswith('.json'):
                    with open(os.path.join(metadata_dir, filename), 'r', encoding='utf-8') as f:
                        doc_meta = json.load(f)
                        documents.append(doc_meta)
        return documents


def display_docs_menu(docs: List[Dict]) -> Optional[Dict]:
    """Display a menu of documents and let user choose one."""
    print("\n" + "=" * 80)
    print("📚 AVAILABLE GOOGLE DOCS")
    print("=" * 80)
    
    if not docs:
        print("No Google Docs found.")
        return None
    
    for i, doc in enumerate(docs, 1):
        name = doc.get('name', 'Untitled')
        doc_id = doc.get('id', '')
        modified = doc.get('modifiedTime', 'Unknown')[:10]
        owners = doc.get('owners', [{'emailAddress': 'Unknown'}])
        owner_email = owners[0].get('emailAddress', 'Unknown') if owners else 'Unknown'
        
        print(f"{i:3}. {name}")
        print(f"     ID: {doc_id}")
        print(f"     Modified: {modified} | Owner: {owner_email}")
        print()
    
    print(f"0. Extract ALL documents")
    print("-" * 80)
    
    while True:
        try:
            choice = input("\nEnter your choice (0-{}): ".format(len(docs)))
            if not choice:
                print("Please enter a number")
                continue
                
            choice = int(choice)
            if choice == 0:
                return {'all': True}
            elif 1 <= choice <= len(docs):
                return {'all': False, 'doc': docs[choice-1]}
            else:
                print(f"Please enter a number between 0 and {len(docs)}")
        except ValueError:
            print("Please enter a valid number")


def main():
    """Main execution function."""
    print("🚀 GOOGLE DOC EXTRACTOR WITH HASH TRACKING")
    print("=" * 80)
    
    # Initialize extractor
    extractor = DocumentExtractor(storage_dir="document_store")
    
    # Show stored documents
    stored_docs = extractor.list_stored_documents()
    if stored_docs:
        print(f"\n📁 Previously stored documents: {len(stored_docs)}")
        for doc in stored_docs:
            print(f"  • {doc.get('document_name', 'Unknown')}")
            print(f"    Hash: {doc.get('current_hash', '')[:16]}...")
            print(f"    Versions: {len(doc.get('versions', []))}")
            print(f"    Last extracted: {doc.get('last_modified', 'Unknown')}")
            print()
    
    # List available Google Docs
    print("\n🔍 Fetching available Google Docs...")
    docs = extractor.list_google_docs(limit=20)
    
    if not docs:
        print("No Google Docs found. Make sure you have documents in your Drive.")
        return
    
    # Let user choose
    choice_result = display_docs_menu(docs)
    
    if not choice_result:
        return
    
    results = []
    
    if choice_result.get('all'):
        # Extract ALL documents
        print(f"\n🔄 Extracting ALL {len(docs)} documents...")
        for doc in docs:
            doc_id = doc['id']
            result = extractor.extract_document(doc_id)
            if 'error' not in result:
                results.append(result)
            else:
                print(f"   ❌ Error extracting {doc_id}: {result['error']}")
    else:
        # Extract single document
        doc = choice_result['doc']
        doc_id = doc['id']
        doc_name = doc.get('name', 'Untitled')
        print(f"\n📝 Selected: {doc_name}")
        
        result = extractor.extract_document(doc_id)
        if 'error' not in result:
            results.append(result)
        else:
            print(f"❌ Error extracting: {result['error']}")
            return
    
    # Show summary
    print("\n" + "=" * 80)
    print("📊 EXTRACTION SUMMARY")
    print("=" * 80)
    
    total_changed = sum(1 for r in results if r.get('changed', False))
    total_new = sum(1 for r in results if not r.get('previous_hash'))
    
    print(f"Total processed: {len(results)}")
    print(f"Changed: {total_changed}")
    print(f"New: {total_new}")
    print(f"Unchanged: {len(results) - total_changed - total_new}")
    
    print("\n✅ Extraction complete!")
    print(f"📂 Documents stored in: document_store/")

if __name__ == "__main__":
    main()
