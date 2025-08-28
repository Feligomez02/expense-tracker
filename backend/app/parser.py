import os
import base64
import hashlib
import re
from datetime import datetime
import pdfplumber
from pdf2image import convert_from_path
import pytesseract

from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

from .database import SessionLocal
from .models import Factura

TOKEN_FILE = "token.json"  # generado en OAuth
DOWNLOAD_FOLDER = "downloads"

# Crear carpeta de PDFs
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# Scopes Gmail
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

# -------------------------
# Funciones de Gmail
# -------------------------
def obtener_service():
    creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    service = build('gmail', 'v1', credentials=creds)
    return service

def buscar_mails(service, query="subject:Factura has:attachment"):
    """Busca mails que contengan 'Factura' en el subject y tengan adjuntos."""
    results = service.users().messages().list(userId='me', q=query).execute()
    messages = results.get('messages', [])
    print(f"Mensajes encontrados: {len(messages)}")
    return messages

def descargar_pdf(service, msg_id):
    """Descarga PDFs adjuntos, renombrando archivos para seguridad en Windows."""
    message = service.users().messages().get(userId='me', id=msg_id).execute()
    parts = message['payload'].get('parts', [])
    pdf_files = []

    for part in parts:
        orig_filename = part.get('filename')
        if orig_filename and orig_filename.lower().endswith(".pdf"):
            # renombrar para evitar path largo o caracteres inválidos
            hash_name = hashlib.sha1(orig_filename.encode()).hexdigest()
            filename = f"{hash_name}.pdf"
            path = os.path.join(DOWNLOAD_FOLDER, filename)

            if 'body' in part and 'attachmentId' in part['body']:
                att_id = part['body']['attachmentId']
                attachment = service.users().messages().attachments().get(
                    userId='me', messageId=msg_id, id=att_id
                ).execute()
                file_data = base64.urlsafe_b64decode(attachment['data'])
            elif 'body' in part and 'data' in part['body']:
                file_data = base64.urlsafe_b64decode(part['body']['data'])
            else:
                continue

            with open(path, "wb") as f:
                f.write(file_data)

            pdf_files.append(path)
    return pdf_files

# -------------------------
# Funciones de extracción
# -------------------------
def extraer_texto(pdf_path):
    """Extrae texto del PDF; si falla, usa OCR."""
    texto = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            texto += page.extract_text() + "\n" if page.extract_text() else ""
    
    # Si texto vacío, usar OCR
    if not texto.strip():
        images = convert_from_path(pdf_path)
        for img in images:
            texto += pytesseract.image_to_string(img) + "\n"
    
    return texto

def extraer_datos_pdf(pdf_path):
    texto = extraer_texto(pdf_path)

    # Extraer monto
    monto_match = re.search(r"\$ ?([\d,.]+)", texto)
    monto = float(monto_match.group(1).replace(",", "")) if monto_match else None

    # Extraer fecha de vencimiento con regex flexible
    vencimiento_match = re.search(
        r"(Vencimiento|Fecha de pago|Pago antes de)[:\s]*([0-3]?\d/[01]?\d/\d{4})",
        texto
    )
    vencimiento_str = vencimiento_match.group(2) if vencimiento_match else None

    # Extraer nombre del servicio/proveedor
    proveedor_match = re.search(r"(Proveedor|De|Emisor)[:\s]*(.+)", texto)
    servicio = proveedor_match.group(2).strip() if proveedor_match else "Servicio Desconocido"

    return {
        "monto": monto,
        "vencimiento": vencimiento_str,
        "servicio": servicio
    }

# -------------------------
# Guardar en DB
# -------------------------
def guardar_factura(servicio, monto, vencimiento_str, pdf_path):
    db = SessionLocal()
    
    # Convertir fecha
    if vencimiento_str:
        try:
            vencimiento_date = datetime.strptime(vencimiento_str, "%d/%m/%Y").date()
        except:
            vencimiento_date = None
    else:
        vencimiento_date = None

    factura = Factura(
        servicio=servicio,
        monto=monto,
        vencimiento=vencimiento_date,
        pdf_path=pdf_path,
        estado="pendiente"
    )
    db.add(factura)
    db.commit()
    db.close()

# -------------------------
# Función principal
# -------------------------
def procesar_facturas():
    service = obtener_service()
    mensajes = buscar_mails(service)
    count = 0

    for msg in mensajes:
        pdfs = descargar_pdf(service, msg['id'])
        for pdf in pdfs:
            datos = extraer_datos_pdf(pdf)
            guardar_factura(datos["servicio"], datos["monto"], datos["vencimiento"], pdf)
            count += 1

    print(f"Facturas procesadas y guardadas: {count}")
    return count
