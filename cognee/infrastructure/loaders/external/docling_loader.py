from typing import List, Optional

from cognee.infrastructure.files.storage import get_file_storage, get_storage_config
from cognee.infrastructure.files.utils.get_file_metadata import get_file_metadata
from cognee.infrastructure.loaders.LoaderInterface import LoaderInterface
from cognee.shared.logging_utils import get_logger

logger = get_logger(__name__)


class DoclingLoader(LoaderInterface):
    @property
    def supported_extensions(self) -> List[str]:
        return [
            "pdf",
            "docx",
            "pptx",
            "xlsx",
            "html",
            "xhtml",
            "md",
            "csv",
            "png",
            "jpg",
            "jpeg",
            "tiff",
            "bmp",
            "webp",
            "tex",
        ]

    @property
    def supported_mime_types(self) -> List[str]:
        return [
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "text/html",
            "text/markdown",
            "text/csv",
            "image/png",
            "image/jpeg",
            "image/tiff",
            "image/bmp",
            "image/webp",
            "application/x-tex",
        ]

    @property
    def loader_name(self) -> str:
        return "docling_loader"

    def can_handle(self, extension: str, mime_type: str) -> bool:
        return extension in self.supported_extensions or mime_type in self.supported_mime_types

    def __init__(self):
        self._converter = None
        self.max_pages_per_chunk = 100

    def _build_converter(self):
        from docling.datamodel.base_models import InputFormat
        from docling.datamodel.pipeline_options import (
            AcceleratorDevice,
            AcceleratorOptions,
            PdfPipelineOptions,
            TableFormerMode,
            TableStructureOptions,
        )
        from docling.document_converter import DocumentConverter

        pdf_options = PdfPipelineOptions(
            do_ocr=True,
            do_code_enrichment=False,
            do_formula_enrichment=True,
            generate_page_images=False,
            generate_picture_images=False,
            images_scale=1.0,
            table_structure_options=TableStructureOptions(
                mode=TableFormerMode.ACCURATE,
                do_cell_matching=True,
            ),
            accelerator_options=AcceleratorOptions(device=AcceleratorDevice.CPU),
        )
        return DocumentConverter(pipeline_options={InputFormat.PDF: pdf_options})

    def _get_converter(self):
        if self._converter is None:
            self._converter = self._build_converter()
        return self._converter

    def _get_page_count(self, file_path: str) -> int:
        from pypdf import PdfReader

        return len(PdfReader(file_path).pages)

    def _convert_and_unload(
        self, converter, file_path: str, page_range: Optional[tuple[int, int]] = None
    ) -> str:
        kwargs = {}
        if page_range is not None:
            kwargs["page_range"] = page_range

        try:
            result = converter.convert(file_path, **kwargs)
        except TypeError:
            # Some docling versions do not expose page_range in convert(); fall back safely.
            result = converter.convert(file_path)

        content = result.document.export_to_markdown()
        if hasattr(result, "input") and hasattr(result.input, "_backend"):
            result.input._backend.unload()
        return content

    async def load(self, file_path: str, **kwargs) -> str:
        converter = self._get_converter()
        ext = file_path.rsplit(".", 1)[-1].lower() if "." in file_path else ""

        if ext == "pdf":
            page_count = self._get_page_count(file_path)
            if page_count <= self.max_pages_per_chunk:
                full_content = self._convert_and_unload(converter, file_path)
            else:
                parts = []
                for start in range(1, page_count + 1, self.max_pages_per_chunk):
                    end = min(start + self.max_pages_per_chunk - 1, page_count)
                    parts.append(
                        self._convert_and_unload(converter, file_path, page_range=(start, end))
                    )
                full_content = "\n\n".join(parts)
        else:
            full_content = self._convert_and_unload(converter, file_path)

        with open(file_path, "rb") as file:
            file_metadata = await get_file_metadata(file)
            storage_file_name = "text_" + file_metadata["content_hash"] + ".txt"

        storage_config = get_storage_config()
        data_root_directory = storage_config["data_root_directory"]
        storage = get_file_storage(data_root_directory)

        return await storage.store(storage_file_name, full_content)
