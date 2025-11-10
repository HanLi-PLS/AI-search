"""
Document processing service for AI search
Handles PDF extraction, document loading, and text splitting
"""
import os
import json
import base64
import tempfile
from typing import List, Dict, Any
from multiprocessing import Pool, cpu_count

import boto3
import fitz  # PyMuPDF
from langchain.docstore.document import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import (
    CSVLoader,
    UnstructuredFileLoader,
    UnstructuredHTMLLoader,
    UnstructuredMarkdownLoader,
    TextLoader,
    UnstructuredExcelLoader,
    Docx2txtLoader,
)
from openai import OpenAI


class DocumentService:
    """Service for processing documents from S3"""

    def __init__(self, openai_api_key: str, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.openai_api_key = openai_api_key
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.s3_client = boto3.client('s3')

        # File extension to loader mapping
        self.loader_mapping = {
            ".csv": (CSVLoader, {}),
            ".html": (UnstructuredHTMLLoader, {}),
            ".md": (UnstructuredMarkdownLoader, {}),
            ".txt": (UnstructuredFileLoader, {"encoding": "utf8"}),
            ".xlsx": (UnstructuredExcelLoader, {}),
            ".docx": (Docx2txtLoader, {}),
        }

    def process_image_with_ai(self, image_base64: str, model: str = "gpt-4o") -> str:
        """Extract information from an image using OpenAI Vision API"""
        max_retries = 3
        attempt = 0

        while attempt < max_retries:
            try:
                client = OpenAI(api_key=self.openai_api_key)
                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": "Please extract information from the following image in detail and precisely.",
                                },
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/png;base64,{image_base64}",
                                    },
                                },
                            ],
                        }
                    ],
                )
                return response.choices[0].message.content
            except Exception as e:
                attempt += 1
                if attempt == max_retries:
                    return f"Error: {str(e)}"
                import time
                time.sleep(2)

    def extract_information_from_page(
        self,
        page: fitz.Page,
        page_number: int,
        model: str,
        source: str,
        scale_factor: float = 1.5
    ) -> Dict[str, Any]:
        """Extract text and image information from a PDF page"""
        text = page.get_text()
        combined_text = [f"Page {page_number + 1} Text:\n{text}\n"]

        # Check if page has tables
        tables = page.find_tables()
        has_tables = len(tables.tables) > 0 if tables else False

        # Check if page has sub-images
        document = fitz.open(page.parent.name)
        image_list = page.get_images(full=True)
        has_sub_images = bool(image_list)

        # Process as image if page has sub-images OR tables
        if has_sub_images or has_tables:
            mat = fitz.Matrix(scale_factor, scale_factor)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            overview_image_base64 = base64.b64encode(pix.tobytes(output="png")).decode("utf-8")

            # Process the page image with AI
            processed_text = self.process_image_with_ai(overview_image_base64, model)
            combined_text.append(f"Page {page_number + 1} Image Information:\n{processed_text}\n")

            result = {
                "text": "\n".join(combined_text),
                "metadata": {
                    "overview_image": overview_image_base64,
                    "source": source,
                    "seq_num": page_number + 1
                }
            }
        else:  # Only plain text on the page
            result = {
                "text": "\n".join(combined_text),
                "metadata": {
                    "source": source,
                    "seq_num": page_number + 1
                }
            }

        return result

    def extract_information_from_pdf(self, pdf_path: str, model: str = "gpt-4o") -> str:
        """Extract information from all pages of a PDF using multiprocessing"""
        doc = fitz.open(pdf_path)
        num_pages = len(doc)

        # Helper function for multiprocessing
        def helper(page_number, pdf_path, model):
            doc = fitz.open(pdf_path)
            page = doc.load_page(page_number)
            return self.extract_information_from_page(page, page_number, model, pdf_path)

        args = [(i, pdf_path, model) for i in range(num_pages)]

        try:
            with Pool(processes=cpu_count()) as pool:
                results = pool.starmap(helper, args)

            extracted_data = [{
                "page_content": result["text"],
                "metadata": result["metadata"]
            } for result in results]

            return json.dumps(extracted_data, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Error during PDF processing: {e}")
            return json.dumps([])

    def load_single_document_from_s3(self, s3_bucket: str, s3_key: str) -> List[Document]:
        """Load a single document from S3"""
        ext = "." + s3_key.rsplit(".", 1)[-1].lower()
        filename = os.path.basename(s3_key)

        retries = 3
        for attempt in range(retries):
            try:
                # Handle JSON (processed PDFs)
                if ext == '.json':
                    obj = self.s3_client.get_object(Bucket=s3_bucket, Key=s3_key)
                    data = json.loads(obj['Body'].read().decode('utf-8'))
                    documents = [
                        Document(page_content=item["page_content"], metadata=item["metadata"])
                        for item in data
                    ]
                    return documents

                # Handle other file types
                if ext in self.loader_mapping:
                    loader_class, loader_args = self.loader_mapping[ext]
                    obj = self.s3_client.get_object(Bucket=s3_bucket, Key=s3_key)
                    file_content = obj['Body'].read()

                    # Write to temporary file
                    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as temp_file:
                        temp_file.write(file_content)
                        temp_file_path = temp_file.name

                    try:
                        loader = loader_class(temp_file_path, **loader_args)
                        documents = loader.load()

                        # Update metadata to include only filename
                        for document in documents:
                            document.metadata['source'] = filename

                        return documents
                    finally:
                        os.remove(temp_file_path)

                raise ValueError(f"Unsupported file extension '{ext}'")

            except Exception as e:
                print(f"Error loading {s3_key}: {e}")
                if attempt < retries - 1:
                    continue
                else:
                    return []

        return []

    def load_documents_from_s3(
        self,
        s3_bucket: str,
        s3_folder: str,
        ignored_files: List[str] = []
    ) -> List[Document]:
        """Load all documents from an S3 folder"""
        to_load = [ext.lower() for ext in self.loader_mapping.keys()] + ['.json']

        # Collect all matching keys using paginator
        s3_keys: List[str] = []
        paginator = self.s3_client.get_paginator('list_objects_v2')

        for page in paginator.paginate(Bucket=s3_bucket, Prefix=s3_folder):
            for obj in page.get('Contents', []):
                key = obj['Key']
                key_lower = key.lower()
                if any(key_lower.endswith(ext) for ext in to_load) and key not in ignored_files:
                    s3_keys.append(key)

        print(f"Found {len(s3_keys)} documents to load")

        # Load documents
        documents: List[Document] = []
        for s3_key in s3_keys:
            docs = self.load_single_document_from_s3(s3_bucket, s3_key)
            documents.extend(docs)

        return documents

    def process_documents_from_s3(
        self,
        s3_bucket: str,
        s3_folder: str,
        ignored_files: List[str] = []
    ) -> List[Document]:
        """Load documents from S3 and split into chunks"""
        print(f"Loading documents from s3://{s3_bucket}/{s3_folder}")
        documents = self.load_documents_from_s3(s3_bucket, s3_folder, ignored_files)

        if not documents:
            print("No documents to load")
            return []

        print(f"Loaded {len(documents)} documents")

        # Split documents
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap
        )
        texts = text_splitter.split_documents(documents)

        # Add filename to each chunk
        for chunk in texts:
            filename = chunk.metadata.get('source', 'unknown_file')
            chunk.page_content = f"From file: {filename}\n\n{chunk.page_content}"

        print(f"Split into {len(texts)} chunks")
        return texts
