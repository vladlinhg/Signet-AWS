import logging
import re
import fitz
from apps.invoices.models import Invoice

logger = logging.getLogger(__name__)

def check_for_duplicate(booking_no: str, raw_text: str) -> bool:
    """
    Duplicate Check & Early Exit.
    Compares the raw PDF text against the latest `SupportingDocument` matching 
    the provided booking number. Strips timestamps to ensure accuracy.
    """
    if not booking_no:
        return False
        
    try:
        invoice = Invoice.objects.filter(booking_number=booking_no).first()
        if not invoice:
            return False
            
        last_doc = invoice.supporting_documents.order_by('-created_at').first()
        if not last_doc or not last_doc.file:
            return False
            
        old_doc = fitz.open(stream=last_doc.file.read(), filetype="pdf")
        old_raw = ""
        for page in old_doc:
            old_raw += page.get_text("text") + "\n"
            
        timestamp_pattern = r'\d{1,2}/\d{1,2}/\d{4}\s+\d{1,2}:\d{2}\s+(AM|PM)'
        
        clean_old = re.sub(timestamp_pattern, "", old_raw).strip()
        clean_new = re.sub(timestamp_pattern, "", raw_text).strip()
        
        if clean_old == clean_new:
            logger.info(f"Duplicate Import aborted for booking {booking_no}")
            return True
            
    except Exception as e:
        logger.warning(f"Error checking duplicate PDF text: {e}")
        
    return False
