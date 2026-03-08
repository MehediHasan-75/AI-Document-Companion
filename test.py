from unstructured.partition.pdf import partition_pdf

output_path = ""
file_path = 'uploads/407a7dea-0a93-4aea-82df-c3b4aa3c6d97.pdf'

# Reference: https://docs.unstructured.io/open-source/core-functionality/chunking
#  list[CompositeElement | Table | Image]
# CompositeElement → grouped text chunk (section-based)
# Table → structured table object
# Image → if extracted

chunks = partition_pdf(
    filename=file_path,
    infer_table_structure=True,            # extract tables
    strategy="hi_res",                     # mandatory to infer tables

    extract_image_block_types=["Image"],   # Add 'Table' to list to extract image of tables
    # image_output_dir_path=output_path,   # if None, images and tables will saved in base64

    extract_image_block_to_payload=True,   # if true, will extract base64 for API usage

    chunking_strategy="by_title",          # or 'basic'
    max_characters=10000,                  # defaults to 500
    combine_text_under_n_chars=2000,       # defaults to 0
    new_after_n_chars=6000,

    # extract_images_in_pdf=True,          # deprecated
)
for chunk in chunks:
    # 1. Identify the building block type (CompositeElement, Table, etc.)
    chunk_type = type(chunk).__name__
    print(f"\n--- {chunk_type} ---")
    
    # 2. Print the actual text or extracted table data
    print("Text Content:", chunk.text)
    
    # 3. Check for the base64 image payload you enabled in your parameters
    if chunk.metadata.image_base64:
        print("📸 [Base64 Image Data Extracted!]")