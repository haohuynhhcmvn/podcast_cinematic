def generate_hash(text):
    import hashlib
    return hashlib.sha1(text.encode('utf-8')).hexdigest()
# Placeholder for utils functions
