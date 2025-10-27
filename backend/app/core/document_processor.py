"""
Document processing utilities
Adapted from existing code in old_coding/docIndex.ipynb
"""
import os
import json
import base64
from typing import List, Dict, Any
from pathlib import Path
import fitz  # PyMuPDF
from langchain_core.documents import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import (
    CSVLoader,
    UnstructuredFileLoader,
    UnstructuredHTMLLoader,
    UnstructuredMarkdownLoader,
    TextLoader,
    Docx2txtLoader,
    UnstructuredExcelLoader,
)
from openai import OpenAI
from backend.app.config import settings
import time
import logging

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """Process documents and extract text content"""

    def __init__(self):
        self.client = OpenAI(api_key=settings.get_openai_api_key())
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP
        )
        self.vision_model = settings.VISION_MODEL

        # Map file extensions to document loaders
        self.LOADER_MAPPING = {
            ".csv": (CSVLoader, {}),
            ".html": (UnstructuredHTMLLoader, {}),
            ".htm": (UnstructuredHTMLLoader, {}),
            ".md": (UnstructuredMarkdownLoader, {}),
            ".txt": (TextLoader, {"encoding": "utf-8"}),
            ".xlsx": (UnstructuredExcelLoader, {}),
            ".xls": (UnstructuredExcelLoader, {}),
            ".docx": (Docx2txtLoader, {}),
            ".doc": (Docx2txtLoader, {}),
            ".eml": (UnstructuredFileLoader, {}),
        }

    def process_file(self, file_path: Path, file_name: str) -> List[Document]:
        """
        Process a single file and return list of document chunks

        Args:
            file_path: Path to the file
            file_name: Original file name

        Returns:
            List of Document objects
        """
        ext = file_path.suffix.lower()
        logger.info(f"Processing file: {file_name} with extension: {ext}")

        try:
            if ext == ".pdf":
                documents = self._process_pdf(file_path, file_name)
            elif ext == ".json":
                documents = self._process_json(file_path, file_name)
            elif ext in self.LOADER_MAPPING:
                documents = self._process_with_loader(file_path, file_name, ext)
            else:
                raise ValueError(f"Unsupported file extension: {ext}")

            # Split documents into chunks
            chunks = self.text_splitter.split_documents(documents)

            # Add filename to each chunk after splitting (from old code pattern)
            for chunk in chunks:
                filename = chunk.metadata.get('source', 'unknown_file')
                chunk.page_content = f"From file: {filename}\n\n{chunk.page_content}"

            logger.info(f"Created {len(chunks)} chunks from {file_name}")

            return chunks

        except Exception as e:
            logger.error(f"Error processing file {file_name}: {str(e)}")
            raise

    def _process_with_loader(self, file_path: Path, file_name: str, ext: str) -> List[Document]:
        """Process file using LangChain loaders"""
        loader_class, loader_args = self.LOADER_MAPPING[ext]
        loader = loader_class(str(file_path), **loader_args)
        documents = loader.load()

        # Update metadata
        for doc in documents:
            doc.metadata["source"] = file_name
            doc.metadata["file_type"] = ext

        return documents

    def _process_json(self, file_path: Path, file_name: str) -> List[Document]:
        """Process JSON files (from PDF extraction)"""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        documents = []
        for item in data:
            metadata = item.get("metadata", {}).copy()
            metadata["source"] = file_name
            metadata["file_type"] = ".json"
            documents.append(
                Document(
                    page_content=item["page_content"],
                    metadata=metadata
                )
            )

        return documents

    def _process_pdf(self, file_path: Path, file_name: str) -> List[Document]:
        """
        Process PDF with image extraction using vision model (o4-mini or gpt-4o)
        Adapted from extract_information_from_pdf in old code
        """
        logger.info(f"Processing PDF: {file_name} with model: {self.vision_model}")
        doc = fitz.open(str(file_path))
        documents = []

        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            result = self._extract_information_from_page(page, page_num, self.vision_model, file_name)

            documents.append(
                Document(
                    page_content=result["text"],
                    metadata=result["metadata"]
                )
            )

        doc.close()
        logger.info(f"Processed {len(documents)} pages from PDF: {file_name}")
        return documents

    def _extract_information_from_page(
        self, page: fitz.Page, page_number: int, model: str, source: str, scale_factor: float = 1.5
    ) -> Dict[str, Any]:
        """
        Extract information from a PDF page
        Checks for tables and sub-images before processing with AI
        """
        text = page.get_text()
        combined_text = [f"Page {page_number + 1} Text:\n{text}\n"]

        # Check if page has tables
        tables = page.find_tables()
        has_tables = len(tables.tables) > 0 if tables else False

        # Check if page has sub-images
        image_list = page.get_images(full=True)
        has_sub_images = len(image_list) > 0

        # Process as image if page has sub-images OR tables
        if has_sub_images or has_tables:
            # Increase resolution using scale factor
            mat = fitz.Matrix(scale_factor, scale_factor)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            overview_image_base64 = base64.b64encode(pix.tobytes(output="png")).decode("utf-8")

            # Process the page image with AI
            processed_text = self._process_image_with_ai(overview_image_base64, model)
            combined_text.append(f"Page {page_number + 1} Image Information:\n{processed_text}\n")

            result = {
                "text": "\n".join(combined_text),
                "metadata": {
                    "source": source,
                    "file_type": ".pdf",
                    "page": page_number + 1,
                    "has_images": True,
                    "has_tables": has_tables
                }
            }
        else:  # Only plain text on the page
            result = {
                "text": "\n".join(combined_text),
                "metadata": {
                    "source": source,
                    "file_type": ".pdf",
                    "page": page_number + 1,
                    "has_images": False,
                    "has_tables": False
                }
            }

        return result

    def _process_image_with_ai(self, image_base64: str, model: str) -> str:
        """Process image using GPT-4 Vision"""
        max_retries = 5
        attempt = 0

        while attempt < max_retries:
            try:
                response = self.client.chat.completions.create(
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
                    logger.error(f"Failed to process image after {max_retries} attempts: {str(e)}")
                    return f"Error processing image: {str(e)}"
                time.sleep(2)  # Wait before retrying

        return ""
