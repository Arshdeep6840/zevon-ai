from ...core.tools import registry
from . import auth


def search_files(query: str, max_results: int = 10):
    q = query.replace("'", "\\'")
    r = auth.service("drive", "v3").files().list(q=f"name contains '{q}' and trashed=false", pageSize=max_results,
                                                 fields="files(id,name,mimeType,modifiedTime)").execute()
    return "\n".join(f"[{f['id']}] {f['name']} ({f['mimeType']}, {f['modifiedTime'][:10]})"
                     for f in r.get("files", [])) or "No files found."


def read_file(file_id: str):
    files = auth.service("drive", "v3").files()
    meta = files.get(fileId=file_id, fields="name,mimeType").execute()
    mime = meta["mimeType"]
    if mime == "application/vnd.google-apps.document":
        data = files.export(fileId=file_id, mimeType="text/plain").execute()
    elif mime == "application/vnd.google-apps.spreadsheet":
        data = files.export(fileId=file_id, mimeType="text/csv").execute()
    elif mime.startswith("text/") or mime == "application/json":
        data = files.get_media(fileId=file_id).execute()
    else:
        return f"Unsupported file type for text reading: {mime}"
    text = data.decode(errors="replace") if isinstance(data, bytes) else str(data)
    return f"{meta['name']}\n\n{text[:4000]}"


def create_doc(name: str, content: str):
    """Create a NEW Google Doc from text. (drive.file scope: Zevon can only touch files it created.)"""
    import io
    from googleapiclient.http import MediaIoBaseUpload
    media = MediaIoBaseUpload(io.BytesIO(content.encode()), mimetype="text/plain")
    f = auth.service("drive", "v3").files().create(
        body={"name": name, "mimeType": "application/vnd.google-apps.document"}, media_body=media,
        fields="id,webViewLink").execute()
    return f"Created Google Doc: {f.get('webViewLink', f['id'])}"


def register():
    registry.tool("drive_search_files", "Search Google Drive files by name.", {"type": "object", "properties": {
        "query": {"type": "string"}, "max_results": {"type": "integer"}}, "required": ["query"]}, risk="read")(search_files)
    registry.tool("drive_read_file", "Read a Google Doc/Sheet/text file from Drive by id.", auth.obj(file_id="string"),
                  risk="read")(read_file)
    registry.tool("drive_create_doc", "Create a new Google Doc with the given text.", auth.obj(name="string", content="string"),
                  risk="safe_write")(create_doc)
