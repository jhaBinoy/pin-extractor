import streamlit as st
import re
import base64
import zlib

def decode_viewstate(html_content):
    """
    Extracts the __VIEWSTATE value from HTML, Base64 decodes it,
    attempts zlib decompression, and then decodes as text.
    """
    # UPDATED REGEX FOR __VIEWSTATE EXTRACTION:
    # This regex is more tolerant to attribute order within the <input> tag.
    # It looks for 'name="__VIEWSTATE"' and then the 'value' attribute within the same tag.
    # [^>]* matches any character that is NOT a closing angle bracket, zero or more times,
    # effectively skipping other attributes between 'name' and 'value'.
    match = re.search(r'name="__VIEWSTATE"[^>]*value="([^"]*)"', html_content, re.IGNORECASE)
    
    if not match:
        print("Error: __VIEWSTATE not found in the HTML content by regex.")
        # Print the beginning of the content that failed to match for deeper inspection
        print(f"DEBUG: Content that failed to match (first 200 chars): '{html_content[:200]}'...")
        return None

    encoded_string = match.group(1)
    
    try:
        # Base64 decode the string
        decoded_bytes = base64.b64decode(encoded_string)
        print(f"Raw bytes after Base64 decoding: {decoded_bytes[:100]}...")

        # Try zlib decompression first (common for __VIEWSTATE in ASP.NET)
        try:
            decompressed_bytes = zlib.decompress(decoded_bytes)
            print("Successfully decompressed with zlib.")
            try:
                decoded_content = decompressed_bytes.decode('utf-8')
                print("Successfully decoded zlib decompressed bytes as UTF-8.")
            except UnicodeDecodeError:
                decoded_content = decompressed_bytes.decode('latin-1')
                print("Successfully decoded zlib decompressed bytes as latin-1.")
            return decoded_content
        except zlib.error as e:
            print(f"Zlib decompression failed: {e}. Attempting direct text decoding.")
            try:
                decoded_content = decoded_bytes.decode('utf-8')
                print("Successfully decoded raw Base64 bytes as UTF-8.")
            except UnicodeDecodeError as e_utf8:
                print(f"UTF-8 decoding failed: {e_utf8}. Attempting latin-1 decoding.")
                try:
                    decoded_content = decoded_bytes.decode('latin-1')
                    print("Successfully decoded raw Base64 bytes as latin-1.")
                except UnicodeDecodeError as e_latin1:
                    print(f"Latin-1 decoding also failed: {e_latin1}. Data might be purely binary or in an unknown format.")
                    return f"Could not decode as text. Raw Base64 decoded bytes (hex): {decoded_bytes.hex()}"
            return decoded_content

    except base64.binascii.Error as e:
        print(f"Base64 decoding failed: {e}. Check if the input string is valid Base64.")
        return None
    except Exception as e:
        print(f"An unexpected error occurred during Base64 processing: {e}")
        return None

def extract_pin_value(decoded_string):
    """
    Finds and extracts a 6-digit numerical value immediately after "PIN" (case-insensitive).
    Handles non-printable characters between "PIN" and the digits.

    Args:
        decoded_string: The string to search within.

    Returns:
        The 6-digit PIN as a string if found, otherwise None.
    """
    if not decoded_string:
        return None

    # Regex to find "PIN", followed by any characters (non-greedy), 
    # then a 6-digit number that is not preceded by another digit.
    pattern = r'PIN(.*?)(?<!\d)(\d{6})' 
    
    match = re.search(pattern, decoded_string, re.IGNORECASE)

    if match:
        return match.group(2) # group(2) captures the 6 digits
    else:
        return None

# --- Main Streamlit execution ---
if __name__ == "__main__":
    st.title("VIEWSTATE PIN Extractor")
    st.markdown("""
        This app extracts the 6-digit PIN from a Base64-encoded `__VIEWSTATE` value
        found in an HTML input string.
    """)

    html_input = st.text_area("Paste your HTML string here:", height=200)
    uploaded_file = st.file_uploader("Or upload an HTML file (.txt, .html):", type=["txt", "html"])
    process_button = st.button("Extract PIN")

    if process_button:
        source_content = ""
        if html_input:
            source_content = html_input
            print(f"DEBUG: Content from text area (first 100 chars): {source_content[:100]}...")
            print(f"DEBUG: Content length from text area: {len(source_content)}")
        elif uploaded_file is not None:
            try:
                # IMPORTANT: For Streamlit file uploader, .read() returns bytes.
                # You *must* decode these bytes to a string before passing to regex.
                # Keep utf-8 for file read initially, as it's common.
                source_content = uploaded_file.read().decode("utf-8") 
                print(f"DEBUG: Content from uploaded file (first 100 chars): {source_content[:100]}...")
                print(f"DEBUG: Content length from uploaded file: {len(source_content)}")
            except Exception as e:
                st.error(f"Error reading or decoding uploaded file: {e}")
                print(f"DEBUG: Error reading uploaded file: {e}")
                source_content = "" # Ensure source_content is empty on error
        
        if source_content:
            st.subheader("Processing Results:")
            decoded_content = decode_viewstate(source_content)

            if decoded_content:
                pin_value = extract_pin_value(decoded_content)
                if pin_value:
                    st.success(f"**Extracted PIN: {pin_value}**")
                    st.download_button(
                        label="Download PIN",
                        data=pin_value,
                        file_name="extracted_pin.txt",
                        mime="text/plain"
                    )
                else:
                    st.warning("PIN (6-digit numerical value) not found in the decoded content.")
            else:
                st.error("Failed to decode __VIEWSTATE content. Please check your input or the terminal for debug messages.")
                print("DEBUG: decode_viewstate returned None.")
        else:
            st.info("Please paste some HTML or upload a file to begin.")
            print("DEBUG: source_content was empty.")

    st.info("Remember to place your `decode_viewstate` and `extract_pin_value` functions at the top of your `app.py` file!")