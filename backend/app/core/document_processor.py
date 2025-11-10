"""
Document processing utilities
Adapted from existing code in old_coding/docIndex.ipynb
"""
import os
import json
import base64
from typing import List, Dict, Any
from pathlib import Path
from multiprocessing import Pool, cpu_count
import fitz  # PyMuPDF
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import (
    CSVLoader,
    UnstructuredFileLoader,
    UnstructuredHTMLLoader,
    UnstructuredMarkdownLoader,
    TextLoader,
    Docx2txtLoader,
    UnstructuredExcelLoader,
)
from openai import OpenAI, AsyncOpenAI
import asyncio
from backend.app.config import settings
import time
import logging

logger = logging.getLogger(__name__)


# Helper function for multiprocessing (must be at module level)
def _process_page_helper(page_number: int, pdf_path: str, model: str, file_name: str, scale_factor: float = 1.5) -> Dict[str, Any]:
    """
    Helper function to process a single PDF page (for multiprocessing)

    Args:
        page_number: Page number to process
        pdf_path: Path to the PDF file
        model: Vision model to use (o4-mini)
        file_name: Original filename
        scale_factor: Scale factor for image rendering

    Returns:
        Dictionary with page_content and metadata
    """
    doc = fitz.open(pdf_path)
    page = doc.load_page(page_number)

    # Get text from page
    text = page.get_text()
    combined_text = [f"Page {page_number + 1} Text:\n{text}\n"]

    # Check if page has tables
    tables = page.find_tables()
    has_tables = len(tables.tables) > 0 if tables else False

    # Check if page has sub-images
    image_list = page.get_images(full=True)
    has_sub_images = len(image_list) > 0

    # Process as image if page has sub-images OR tables (using o4-mini)
    if has_sub_images or has_tables:
        logger.info(f"Page {page_number + 1} has images/tables, processing with {model}")

        # Increase resolution using scale factor
        mat = fitz.Matrix(scale_factor, scale_factor)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        overview_image_base64 = base64.b64encode(pix.tobytes(output="png")).decode("utf-8")

        # Process the page image with AI (o4-mini for vision)
        processed_text = _process_image_with_ai_helper(overview_image_base64, model)
        combined_text.append(f"Page {page_number + 1} Image Information:\n{processed_text}\n")

        result = {
            "page_content": "\n".join(combined_text),
            "metadata": {
                "source": file_name,
                "file_type": ".pdf",
                "page": page_number + 1,
                "has_images": True,
                "has_tables": has_tables
            }
        }
    else:  # Only plain text on the page
        result = {
            "page_content": "\n".join(combined_text),
            "metadata": {
                "source": file_name,
                "file_type": ".pdf",
                "page": page_number + 1,
                "has_images": False,
                "has_tables": False
            }
        }

    doc.close()
    return result


async def _process_page_helper_async(page_number: int, pdf_path: str, model: str, file_name: str, api_key: str, scale_factor: float = 1.5) -> Dict[str, Any]:
    """
    Async helper function to process a single PDF page

    Args:
        page_number: Page number to process
        pdf_path: Path to the PDF file
        model: Vision model to use (o4-mini)
        file_name: Original filename
        api_key: OpenAI API key
        scale_factor: Scale factor for image rendering

    Returns:
        Dictionary with page_content and metadata
    """
    doc = fitz.open(pdf_path)
    page = doc.load_page(page_number)

    # Get text from page
    text = page.get_text()
    combined_text = [f"Page {page_number + 1} Text:\n{text}\n"]

    # Check if page has tables
    tables = page.find_tables()
    has_tables = len(tables.tables) > 0 if tables else False

    # Check if page has sub-images
    image_list = page.get_images(full=True)
    has_sub_images = len(image_list) > 0

    # Process as image if page has sub-images OR tables (using o4-mini)
    if has_sub_images or has_tables:
        logger.info(f"Page {page_number + 1} has images/tables, processing with {model} (async)")

        # Increase resolution using scale factor
        mat = fitz.Matrix(scale_factor, scale_factor)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        overview_image_base64 = base64.b64encode(pix.tobytes(output="png")).decode("utf-8")

        # Process the page image with AI asynchronously (o4-mini for vision)
        processed_text = await _process_image_with_ai_helper_async(overview_image_base64, model, api_key)
        combined_text.append(f"Page {page_number + 1} Image Information:\n{processed_text}\n")

        result = {
            "page_content": "\n".join(combined_text),
            "metadata": {
                "source": file_name,
                "file_type": ".pdf",
                "page": page_number + 1,
                "has_images": True,
                "has_tables": has_tables
            }
        }
    else:  # Only plain text on the page
        result = {
            "page_content": "\n".join(combined_text),
            "metadata": {
                "source": file_name,
                "file_type": ".pdf",
                "page": page_number + 1,
                "has_images": False,
                "has_tables": False
            }
        }

    doc.close()
    return result


async def _process_image_with_ai_helper_async(image_base64: str, model: str, api_key: str) -> str:
    """Async helper function to process image with AI using AsyncOpenAI"""
    max_retries = 5
    attempt = 0

    while attempt < max_retries:
        try:
            client = AsyncOpenAI(api_key=api_key)
            response = await client.chat.completions.create(
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
            await asyncio.sleep(2)  # Wait before retrying

    return ""


def _process_image_with_ai_helper(image_base64: str, model: str) -> str:
    """Synchronous wrapper for backward compatibility (fallback mode)"""
    from backend.app.utils.aws_secrets import get_key

    max_retries = 5
    attempt = 0

    while attempt < max_retries:
        try:
            # Get API key using the same method as user's old code
            if settings.USE_AWS_SECRETS:
                api_key = get_key(settings.AWS_SECRET_NAME_OPENAI, settings.AWS_REGION)
            else:
                api_key = settings.OPENAI_API_KEY

            client = OpenAI(api_key=api_key)
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
                logger.error(f"Failed to process image after {max_retries} attempts: {str(e)}")
                return f"Error processing image: {str(e)}"
            time.sleep(2)  # Wait before retrying

    return ""


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
        Process PDF with async parallel processing for vision model calls
        Uses asyncio.gather() to process all pages concurrently for maximum speed
        Adapted from extract_information_from_pdf in old code
        """
        logger.info(f"Processing PDF: {file_name} with model: {self.vision_model}")

        # Get number of pages
        doc = fitz.open(str(file_path))
        num_pages = len(doc)
        doc.close()

        logger.info(f"PDF has {num_pages} pages, using async parallel processing")

        # Get API key once
        from backend.app.utils.aws_secrets import get_key
        if settings.USE_AWS_SECRETS:
            api_key = get_key(settings.AWS_SECRET_NAME_OPENAI, settings.AWS_REGION)
        else:
            api_key = settings.OPENAI_API_KEY

        try:
            # Use asyncio to process all pages concurrently with semaphore limit
            start_time = time.time()

            # Check if we're already in an event loop (FastAPI context)
            try:
                loop = asyncio.get_running_loop()
                # We're in an async context, use run_coroutine_threadsafe or create task
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    results = pool.submit(
                        lambda: asyncio.run(self._process_pdf_async(
                            num_pages,
                            str(file_path),
                            file_name,
                            api_key,
                            max_concurrent=settings.MAX_CONCURRENT_VISION_CALLS
                        ))
                    ).result()
            except RuntimeError:
                # No event loop running, safe to use asyncio.run()
                results = asyncio.run(self._process_pdf_async(
                    num_pages,
                    str(file_path),
                    file_name,
                    api_key,
                    max_concurrent=settings.MAX_CONCURRENT_VISION_CALLS
                ))

            elapsed_time = time.time() - start_time

            # Convert results to Document objects
            documents = [
                Document(
                    page_content=result["page_content"],
                    metadata=result["metadata"]
                )
                for result in results
            ]

            logger.info(f"Processed {len(documents)} pages from PDF: {file_name} using async parallel processing in {elapsed_time:.2f}s")
            return documents

        except Exception as e:
            logger.error(f"Error during async PDF processing {file_name}: {str(e)}")
            logger.info(f"Falling back to sequential processing for {file_name}")

            # Fallback to sequential processing if async fails
            doc = fitz.open(str(file_path))
            documents = []

            for page_num in range(num_pages):
                try:
                    result = _process_page_helper(page_num, str(file_path), self.vision_model, file_name)
                    documents.append(
                        Document(
                            page_content=result["page_content"],
                            metadata=result["metadata"]
                        )
                    )
                except Exception as page_error:
                    logger.error(f"Error processing page {page_num + 1} of {file_name}: {str(page_error)}")
                    continue

            doc.close()
            logger.info(f"Processed {len(documents)} pages from PDF: {file_name} (sequential fallback)")
            return documents

    async def _process_pdf_async(self, num_pages: int, pdf_path: str, file_name: str, api_key: str, max_concurrent: int = 10) -> List[Dict[str, Any]]:
        """
        Async helper to process all PDF pages concurrently using asyncio.gather()
        with concurrency limits to prevent API rate limiting

        Args:
            num_pages: Total number of pages
            pdf_path: Path to the PDF file
            file_name: Original filename
            api_key: OpenAI API key
            max_concurrent: Maximum number of concurrent API calls (default: 10)

        Returns:
            List of page results
        """
        # Create semaphore to limit concurrent API calls
        semaphore = asyncio.Semaphore(max_concurrent)

        async def process_with_semaphore(page_num: int):
            """Wrapper to process page with semaphore limit"""
            async with semaphore:
                logger.info(f"Processing page {page_num + 1}/{num_pages} (concurrent limit: {max_concurrent})")
                return await _process_page_helper_async(page_num, pdf_path, self.vision_model, file_name, api_key)

        # Create tasks for all pages
        tasks = [
            process_with_semaphore(i)
            for i in range(num_pages)
        ]

        # Process all pages concurrently with semaphore limit
        logger.info(f"Starting concurrent processing of {num_pages} pages (max {max_concurrent} concurrent)...")
        results = await asyncio.gather(*tasks)
        logger.info(f"Completed concurrent processing of {num_pages} pages")

        return results
