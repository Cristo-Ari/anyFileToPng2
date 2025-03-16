import os
import dash
from dash import dcc, html, Input, Output, State, callback_context, no_update
import base64
import io
import math
from PIL import Image
import colorsys
import webbrowser
import threading
import time

def generate_favicon_base64() -> str:
    image_size_pixels = 32
    generated_favicon_image = Image.new("RGBA", (image_size_pixels, image_size_pixels))
    for horizontal_pixel_index in range(image_size_pixels):
        calculated_hue_value = horizontal_pixel_index / (image_size_pixels - 1)
        calculated_red_value, calculated_green_value, calculated_blue_value = colorsys.hsv_to_rgb(calculated_hue_value, 1, 1)
        calculated_pixel_color = (int(calculated_red_value * 255), int(calculated_green_value * 255), int(calculated_blue_value * 255), 255)
        for vertical_pixel_index in range(image_size_pixels):
            generated_favicon_image.putpixel((horizontal_pixel_index, vertical_pixel_index), calculated_pixel_color)
    generated_image_buffer = io.BytesIO()
    generated_favicon_image.save(generated_image_buffer, format="PNG")
    return base64.b64encode(generated_image_buffer.getvalue()).decode("utf-8")

calculated_favicon_base64_data = generate_favicon_base64()

modified_custom_index_html_template = f"""
<!DOCTYPE html>
<html>
    <head>
        <meta charset="utf-8">
        <title>PNG Converter</title>
        <link rel="icon" type="image/png" href="data:image/png;base64,{calculated_favicon_base64_data}">
        <link rel="shortcut icon" type="image/png" href="data:image/png;base64,{calculated_favicon_base64_data}">
        <style>
            html, body {{
                margin: 0;
                padding: 0;
                height: 100%;
                background-color: #000;
                color: #fff;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            }}
            .app-header {{
                height: 60px;
                text-align: center;
                font-size: 2em;
                line-height: 60px;
                background: linear-gradient(90deg, #0ff, #f0f, #0ff);
                animation: headerAnimation 3s ease-in-out infinite alternate;
            }}
            @keyframes headerAnimation {{
                from {{ filter: brightness(1); }}
                to {{ filter: brightness(1.5); }}
            }}
            .button-zone {{
                display: flex;
                width: 100%;
                height: calc(100% - 60px);
            }}
            .button-half {{
                width: 50%;
                display: flex;
                justify-content: center;
                align-items: center;
                border: 2px dashed #0ff;
                transition: transform 0.3s ease, box-shadow 0.3s ease;
                position: relative;
                overflow: hidden;
            }}
            .button-half:hover {{
                transform: scale(1.03);
                box-shadow: 0 0 20px #0ff;
            }}
            .button-half::before {{
                content: "";
                position: absolute;
                top: -50%;
                left: -50%;
                width: 200%;
                height: 200%;
                background: radial-gradient(circle, rgba(0,255,255,0.2) 0%, transparent 70%);
                transform: rotate(45deg);
                animation: rotateAnimation 5s linear infinite;
                z-index: 0;
            }}
            @keyframes rotateAnimation {{
                from {{ transform: rotate(0deg); }}
                to {{ transform: rotate(360deg); }}
            }}
            .upload-area-content {{
                position: relative;
                z-index: 1;
                font-size: 1.5em;
                font-weight: bold;
                padding: 20px;
                text-align: center;
                cursor: pointer;
            }}
            .message-zone {{
                position: absolute;
                bottom: 10px;
                width: 100%;
                text-align: center;
                font-size: 1.2em;
                color: #0ff;
            }}
            @media (max-width: 768px) {{
                .button-zone {{
                    flex-direction: column;
                }}
                .button-half {{
                    width: 100%;
                    height: 50%;
                }}
            }}
        </style>
        {{%metas%}}{{%css%}}
    </head>
    <body>
        <div class="app-header">PNG Converter</div>
        {{%app_entry%}}
        <footer>{{%config%}}{{%scripts%}}{{%renderer%}}</footer>
    </body>
</html>
"""

def generate_unique_filename_without_conflict(original_base_filename: str, file_extension: str, list_of_existing_file_names: list) -> str:
    unique_filename_candidate = original_base_filename
    counter_for_filename = 1
    while f"{unique_filename_candidate}{file_extension}" in list_of_existing_file_names:
        unique_filename_candidate = f"{original_base_filename} ({counter_for_filename})"
        counter_for_filename += 1
    return f"{unique_filename_candidate}{file_extension}"

def process_encryption_for_file_conversion(original_filename: str, file_data_content: str) -> (bytes, str):
    extracted_header_information, extracted_encoded_file_content = file_data_content.split(',', 1)
    decoded_original_file_bytes = base64.b64decode(extracted_encoded_file_content)
    original_file_extension_bytes = os.path.splitext(original_filename)[1].encode('utf-8')
    file_extension_length_bytes = len(original_file_extension_bytes).to_bytes(1, 'little')
    original_file_size_bytes_length = len(decoded_original_file_bytes)
    file_size_information_bytes = original_file_size_bytes_length.to_bytes(4, 'little')
    concatenated_file_bytes = file_extension_length_bytes + original_file_extension_bytes + file_size_information_bytes + decoded_original_file_bytes
    total_concatenated_bytes_length = len(concatenated_file_bytes)
    calculated_image_dimension = math.ceil(math.sqrt(total_concatenated_bytes_length / 4))
    total_required_image_bytes = calculated_image_dimension * calculated_image_dimension * 4
    padded_concatenated_bytes = concatenated_file_bytes + b'\x00' * (total_required_image_bytes - total_concatenated_bytes_length)
    constructed_rgba_image = Image.frombytes('RGBA', (calculated_image_dimension, calculated_image_dimension), padded_concatenated_bytes)
    output_image_bytes_buffer = io.BytesIO()
    constructed_rgba_image.save(output_image_bytes_buffer, format="PNG")
    safe_generated_download_filename = generate_unique_filename_without_conflict(os.path.splitext(original_filename)[0], ".png", [])
    return output_image_bytes_buffer.getvalue(), safe_generated_download_filename

def process_decryption_for_file_retrieval(original_filename: str, file_data_content: str) -> (bytes, str):
    extracted_header_information, extracted_encoded_file_content = file_data_content.split(',', 1)
    decoded_image_file_bytes = base64.b64decode(extracted_encoded_file_content)
    loaded_rgba_image = Image.open(io.BytesIO(decoded_image_file_bytes)).convert('RGBA')
    extracted_image_data_bytes = loaded_rgba_image.tobytes()
    extracted_file_extension_length = extracted_image_data_bytes[0]
    if len(extracted_image_data_bytes) < 1 + extracted_file_extension_length + 4:
        raise ValueError("Insufficient data to extract file extension and size")
    retrieved_file_extension = extracted_image_data_bytes[1:1 + extracted_file_extension_length].decode('utf-8')
    retrieved_file_size = int.from_bytes(extracted_image_data_bytes[1 + extracted_file_extension_length:1 + extracted_file_extension_length + 4], 'little')
    if len(extracted_image_data_bytes) < 1 + extracted_file_extension_length + 4 + retrieved_file_size:
        raise ValueError("Insufficient data to extract file content")
    recovered_file_data_bytes = extracted_image_data_bytes[1 + extracted_file_extension_length + 4:1 + extracted_file_extension_length + 4 + retrieved_file_size]
    safe_generated_download_filename = generate_unique_filename_without_conflict(os.path.splitext(original_filename)[0], retrieved_file_extension, [])
    return recovered_file_data_bytes, safe_generated_download_filename

application_server_instance = dash.Dash(__name__)
application_server_instance.title = "PNG Converter"
application_server_instance.index_string = modified_custom_index_html_template

application_server_instance.layout = html.Div([
    html.Div([
        dcc.Upload(
            id="upload-encrypt",
            children=html.Div("FILE TO PNG", className="upload-area-content"),
            className="button-half",
            multiple=False
        ),
        dcc.Upload(
            id="upload-decrypt",
            children=html.Div("PNG TO FILE", className="upload-area-content"),
            className="button-half",
            multiple=False
        )
    ], className="button-zone"),
    dcc.Download(id="download-file"),
    html.Div(id="message", className="message-zone")
])

@application_server_instance.callback(
    Output("download-file", "data"),
    Output("message", "children"),
    Input("upload-encrypt", "contents"),
    Input("upload-decrypt", "contents"),
    State("upload-encrypt", "filename"),
    State("upload-decrypt", "filename")
)
def handle_file_upload_and_conversion(encryption_file_content, decryption_file_content, encryption_file_name, decryption_file_name):
    triggered_callback_context = callback_context
    if not triggered_callback_context.triggered:
        return no_update, ""
    triggering_component_identifier = triggered_callback_context.triggered[0]["prop_id"].split(".")[0]
    try:
        if triggering_component_identifier == "upload-encrypt" and encryption_file_content:
            generated_converted_file_bytes, generated_download_file_name = process_encryption_for_file_conversion(encryption_file_name, encryption_file_content)
            return dcc.send_bytes(generated_converted_file_bytes, filename=generated_download_file_name), f"File encrypted and ready for download as {generated_download_file_name}"
        elif triggering_component_identifier == "upload-decrypt" and decryption_file_content:
            generated_converted_file_bytes, generated_download_file_name = process_decryption_for_file_retrieval(decryption_file_name, decryption_file_content)
            return dcc.send_bytes(generated_converted_file_bytes, filename=generated_download_file_name), f"File restored and ready for download as {generated_download_file_name}"
    except Exception as encountered_error:
        return no_update, f"Error: {str(encountered_error)}"
    return no_update, ""

def start_application_server_instance():
    application_server_instance.run_server(debug=False, use_reloader=False)

def launch_browser_with_delay(target_url: str):
    time.sleep(1.5)
    webbrowser.open(target_url)

if __name__ == '__main__':
    designated_server_port = 8050
    designated_server_url = f"http://127.0.0.1:{designated_server_port}/"
    threading.Thread(target=start_application_server_instance).start()
    launch_browser_with_delay(designated_server_url)
