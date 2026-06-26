import fitz  # PyMuPDF
import logging

logger = logging.getLogger(__name__)

MIN_TEXT_LENGTH = 50
MAX_FILE_SIZE = 5 * 1024 * 1024


def _read_pdf_bytes(pdf_file):
    """
    Lee el contenido binario del PDF desde UploadedFile o FileField.
    """
    try:
        if hasattr(pdf_file, "seek"):
            pdf_file.seek(0)

        if hasattr(pdf_file, "read"):
            content = pdf_file.read()

            if hasattr(pdf_file, "seek"):
                pdf_file.seek(0)

            return content

        with open(pdf_file, "rb") as f:
            return f.read()

    except Exception as e:
        logger.error(f"Error leyendo bytes del PDF: {e}")
        raise


def normalize_text(text):
    """
    Limpia el texto extraído del PDF.
    """
    if not text:
        return ""

    lines = []

    for line in text.splitlines():
        cleaned = " ".join(line.strip().split())

        if cleaned:
            lines.append(cleaned)

    return "\n".join(lines).strip()


def extract_text_from_pdf(pdf_file):
    """
    Extrae texto de un PDF usando PyMuPDF.
    Devuelve string vacío si no puede extraer texto suficiente.
    """
    doc = None

    try:
        pdf_bytes = _read_pdf_bytes(pdf_file)
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")

        if doc.is_encrypted:
            logger.warning("PDF protegido o encriptado.")
            return ""

        pages_text = []

        for page_index in range(doc.page_count):
            try:
                page = doc.load_page(page_index)

                # "blocks" suele conservar mejor el orden visual que "text"
                blocks = page.get_text("blocks")
                blocks = sorted(blocks, key=lambda b: (round(b[1], 1), round(b[0], 1)))

                page_lines = []

                for block in blocks:
                    block_text = block[4] if len(block) > 4 else ""
                    block_text = normalize_text(block_text)

                    if block_text:
                        page_lines.append(block_text)

                page_text = normalize_text("\n".join(page_lines))

                if page_text:
                    pages_text.append(page_text)

            except Exception as e:
                logger.warning(f"No se pudo extraer texto de la página {page_index + 1}: {e}")
                continue

        final_text = normalize_text("\n".join(pages_text))

        if len(final_text) < MIN_TEXT_LENGTH:
            logger.warning("Texto insuficiente extraído del PDF.")
            return ""

        return final_text

    except Exception as e:
        logger.error(f"Error extrayendo texto del PDF con PyMuPDF: {e}")
        return ""

    finally:
        if doc is not None:
            try:
                doc.close()
            except Exception:
                pass


def validate_pdf_file(pdf_file):
    """
    Valida que el archivo sea PDF, legible y con al menos una página.
    """
    doc = None

    try:
        if not pdf_file:
            return False, "No se recibió ningún archivo."

        filename = getattr(pdf_file, "name", "").lower()

        if not filename.endswith(".pdf"):
            return False, "Solo se permiten archivos PDF."

        if getattr(pdf_file, "size", 0) > MAX_FILE_SIZE:
            return False, "El archivo no puede superar los 5 MB."

        pdf_bytes = _read_pdf_bytes(pdf_file)
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")

        if doc.is_encrypted:
            return False, "El PDF está protegido o encriptado."

        if doc.page_count == 0:
            return False, "El PDF no contiene páginas."

        return True, "PDF válido."

    except Exception as e:
        logger.error(f"Archivo PDF inválido: {e}")
        return False, f"Archivo PDF inválido: {str(e)}"

    finally:
        if doc is not None:
            try:
                doc.close()
            except Exception:
                pass


def get_pdf_info(pdf_file):
    """
    Obtiene información básica del PDF.
    """
    doc = None

    try:
        pdf_bytes = _read_pdf_bytes(pdf_file)
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")

        metadata = doc.metadata or {}

        return {
            "pages": doc.page_count,
            "title": metadata.get("title") or "Sin título",
            "author": metadata.get("author") or "Sin autor",
            "encrypted": doc.is_encrypted,
        }

    except Exception as e:
        logger.error(f"Error obteniendo información del PDF: {e}")
        return {
            "pages": 0,
            "title": "Error",
            "author": "Error",
            "encrypted": False,
        }

    finally:
        if doc is not None:
            try:
                doc.close()
            except Exception:
                pass