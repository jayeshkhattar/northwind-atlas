import base64

def load_file_block(path):
    data = open(path, "rb").read()
    encoded_bytes = base64.standard_b64encode(data)
    decoded_bytes = encoded_bytes.decode("utf-8")  # check if it's valid UTF-8
    ext = path.lower().rsplit(".", 1)[-1]
    #supported files images, pdf, excel, word, text
    if ext == "png":
        file_type = "image"
        ext_type = "image/png"
    elif ext in ("jpeg", "jpg"):
        file_type = "image"
        ext_type = "image/jpeg"
    elif ext == "pdf":
        file_type = "document"
        ext_type = "application/pdf"
    else:
        raise ValueError(f"Unsupported file type: .{ext}")

    result = {
        "type": file_type,
        "source": {
            "type": "base64",
            "media_type": ext_type,
            "data": decoded_bytes
        }
    }
    return result