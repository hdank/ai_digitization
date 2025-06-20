class ContextService:
    """Service class for preparing context information for AI processing"""
    
    @staticmethod
    def prepare_odoo_context(record_info, attachment):
        """Prepare context information about the current Odoo record and model"""
        # Check attachment first
        if attachment and hasattr(attachment, 'res_model') and attachment.res_model:
            return attachment.res_model
        
        # Check record_info if provided
        if record_info and isinstance(record_info, dict):
            if 'model' in record_info:
                return record_info['model']
            elif 'res_model' in record_info:
                return record_info['res_model']
        
        return "General document processing"
