import logging
from django.db import transaction

from .duplications import check_for_duplicate
from .level_0_reference import import_level_0
from .level_1_primary import import_level_1
from .level_2_secondary import import_level_2
from .level_3_tertiary import import_level_3

logger = logging.getLogger(__name__)

class DryRunException(Exception):
    pass

class BookingImportService:
    """
    Handles updating or creating Data Models using the deeply normalized JSON 
    provided by the `normalize_booking_text` parser.
    Refactored to split operations via topological sorted helpers.
    """
    
    def __init__(self, data: dict, dry_run: bool = True, file_bytes: bytes = None, filename: str = None):
        self.data = data
        self.dry_run = dry_run
        self.file_bytes = file_bytes
        self.filename = filename
        
        self.diff = {
            "created": {"clients": 0, "invoices": 0, "tour_bookings": 0, "flights": 0, "items": 0},
            "updated": {"clients": 0, "invoices": 0, "tour_bookings": 0, "flights": 0},
            "deleted": {"items": 0, "payments": 0}
        }
        
    def execute(self):
        """
        Runs the full import process.
        Will intentionally throw `TransactionRollbackException` if dry_run=True.
        """
        try:
            with transaction.atomic():
                # 0. Duplicate Bypass
                booking_no = self.data.get('invoice', {}).get('lookup_key', {}).get('booking_number')
                raw_text = self.data.get('raw_text_preview', '')
                if check_for_duplicate(booking_no, raw_text):
                    self.diff['status'] = 'NO_CHANGES'
                    return self.diff
                    
                import_level_0(self.data)
                import_level_1(self.data, self.diff)
                import_level_2(self.data, self.diff)
                import_level_3(self.data, self.diff, self.file_bytes, self.filename)
                
                # Report successful diff structure
                self.diff['status'] = 'SUCCESS'
                
                if self.dry_run:
                    raise DryRunException("Dry Run Completed Successfully")
                    
        except DryRunException:
            pass # Expected fallback during preview
            
        except Exception as e:
            logger.error(f"Import Failed: {e}")
            raise e
            
        return self.diff
