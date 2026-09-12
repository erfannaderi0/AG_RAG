Current behavior(extract_and_store file):

**list_google_docs()**
Drive API, lists up to 20 docs
        **↓**
**extract_document()**
fetches doc + calls _get_document_metadata()
        **↓**
**_extract_*_elements()**
plain text + structured json, per tab
        **↓**
**_calculate_hash()**
SHA-256 of the full extracted text
        **↓**
**_get_stored_version()**
loads prior hash, diffs against it
        **↓**
**_store_document()**
only if changed, new, or forced
