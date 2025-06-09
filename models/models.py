# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError
import requests
import json
import base64
import logging

_logger = logging.getLogger(__name__)

class AIDigitizationTemplate(models.Model):
    _name = 'ai_digitization.template'
    _description = 'AI Digitization Template'

    name = fields.Char('Template Name', required=True)
    model_id = fields.Many2one('ir.model', string='Target Odoo Model', required=True, ondelete='cascade')
    model_name = fields.Char(related='model_id.model', string='Model Name', readonly=True)
    document_type = fields.Selection([
        ('handwritten', 'Handwritten Document'),
        ('printed_pdf', 'Printed PDF Document'),
        ('invoice', 'Invoice/Receipt'),
        ('form', 'Form Document'),
        ('mixed', 'Mixed Content'),
        ('custom', 'Custom')
    ], string='Document Type', required=True, default='mixed')
    prompt_template = fields.Selection([
        ('general', 'General Document Extraction'),
        ('handwritten', 'Handwritten Text Recognition'),
        ('invoice', 'Invoice/Receipt Processing'),
        ('form', 'Form Data Extraction'),
        ('custom', 'Custom Prompt')
    ], string='Prompt Template', required=True, default='general')
    prompt_text = fields.Text(
        'Custom Prompt Text', 
        help="Leave empty to use predefined template or write your custom prompt"
    )
    ai_model = fields.Selection([
        ('gemini-2.0-flash', 'Gemini 2.0 Flash'),
        ('gemini-1.5-pro', 'Gemini 1.5 Pro'),
        ('gemini-1.5-flash', 'Gemini 1.5 Flash'),
    ], string='AI Model', required=True, default='gemini-2.0-flash')
    api_key = fields.Char('API Key', help="API Key for the selected AI model", default="your_key_is_here")
    field_mappings = fields.One2many('ai_digitization.field.mapping', 'template_id', string='Field Mappings')
    
    @api.model
    def _get_predefined_prompts(self):
        """Return predefined prompt templates"""
        return {
            'general': """Analyze this document and extract all relevant information. Return the data as a clean JSON object with descriptive field names. Focus on:
- Text content (both typed and handwritten)
- Names, dates, numbers, addresses
- Any structured data like tables or forms
- Key-value pairs and labeled information

Please ensure all text is accurately transcribed, including handwritten content.""",
            
            'handwritten': """This document contains handwritten text. Please carefully analyze and transcribe all handwritten content with high accuracy. Pay special attention to:
- Cursive and printed handwriting
- Numbers and dates
- Names and signatures
- Form fields that are filled in by hand

Return the extracted data as a JSON object with clear field names representing the handwritten content.""",
            
            'invoice': """This is an invoice or receipt document. Extract the following information and return as JSON:
- vendor_name: Company/vendor name
- invoice_number: Invoice or receipt number
- date: Invoice date
- due_date: Due date (if present)
- total_amount: Total amount
- subtotal: Subtotal (if present)
- tax_amount: Tax amount
- currency: Currency
- items: List of line items with description, quantity, unit_price
- customer_info: Customer name and address
- vendor_address: Vendor address

Ensure all monetary values are extracted as numbers.""",
            
            'form': """This document appears to be a form with labeled fields. Extract all filled-in information and return as JSON. Focus on:
- Field labels and their corresponding values
- Checkboxes and their states (checked/unchecked)
- Dropdown selections
- Text areas and input fields
- Dates, signatures, and stamps

Structure the JSON with field labels as keys and filled values as values."""
        }
    
    @api.depends('prompt_template', 'prompt_text')
    def _compute_final_prompt(self):
        """Compute the final prompt to use"""
        for record in self:
            if record.prompt_template == 'custom' and record.prompt_text:
                record.final_prompt = record.prompt_text
            else:
                predefined = self._get_predefined_prompts()
                record.final_prompt = predefined.get(record.prompt_template, predefined['general'])
    
    final_prompt = fields.Text('Final Prompt', compute='_compute_final_prompt', store=True)
    
    # Test document processing fields
    test_document = fields.Binary('Test Document', attachment=True)
    test_document_filename = fields.Char('Test Document Filename')
    test_document_mimetype = fields.Char('Test Document MIME Type', compute='_compute_test_mimetype')
    test_extracted_data = fields.Text('Test Extracted Data', readonly=True)
    test_processing_state = fields.Selection([
        ('draft', 'Ready'),
        ('processing', 'Processing'),
        ('done', 'Completed'),
        ('error', 'Error')
    ], string='Test Processing State', default='draft')
    test_error_message = fields.Text('Test Error Message', readonly=True)
    
    @api.depends('test_document_filename')
    def _compute_test_mimetype(self):
        """Compute MIME type for test document"""
        for record in self:
            if record.test_document_filename:
                filename = record.test_document_filename.lower()
                if filename.endswith('.pdf'):
                    record.test_document_mimetype = 'application/pdf'
                elif filename.endswith(('.jpg', '.jpeg')):
                    record.test_document_mimetype = 'image/jpeg'
                elif filename.endswith('.png'):
                    record.test_document_mimetype = 'image/png'
                elif filename.endswith(('.tiff', '.tif')):
                    record.test_document_mimetype = 'image/tiff'
                elif filename.endswith('.webp'):
                    record.test_document_mimetype = 'image/webp'
                elif filename.endswith('.gif'):
                    record.test_document_mimetype = 'image/gif'
                else:
                    # Default to PNG for unknown image types - Gemini supports this
                    record.test_document_mimetype = 'image/png'
            else:
                record.test_document_mimetype = False
    
    def process_test_document(self):
        """Process the test document using current template"""
        self.ensure_one()
        if not self.test_document:
            raise UserError("Please upload a document first.")
        
        self.test_processing_state = 'processing'
        self.test_error_message = False
        
        try:
            # Process document using Gemini AI
            extracted_data = self._process_document_with_ai(
                self.test_document, 
                self.test_document_filename,
                self.test_document_mimetype
            )
            
            self.test_extracted_data = json.dumps(extracted_data, indent=2)
            self.test_processing_state = 'done'
            
            # Use custom action to show notification and reload form
            return {
                'type': 'ir.actions.client',
                'tag': 'reload_form_with_notification',
                'params': {
                    'notification': {
                        'title': 'Success',
                        'message': 'Document processed successfully! The extracted data is shown below.',
                        'type': 'success',
                        'sticky': False,
                    }
                }
            }
            
        except Exception as e:
            self.test_processing_state = 'error'
            self.test_error_message = str(e)
            
            # Use custom action to show error notification and reload form
            return {
                'type': 'ir.actions.client',
                'tag': 'reload_form_with_notification',
                'params': {
                    'notification': {
                        'title': 'Processing Error',
                        'message': f'Failed to process document: {str(e)}',
                        'type': 'danger',
                        'sticky': True,
                    },
                    'reload_action': {
                        'type': 'ir.actions.act_window',
                        'res_model': 'ai_digitization.template',
                        'res_id': self.id,
                        'view_mode': 'form',
                        'target': 'current',
                    }
                }
            }
    
    def create_processor_record(self):
        """Create a processor record with the uploaded test document"""
        self.ensure_one()
        if not self.test_document:
            raise UserError("Please upload a document first.")
        
        processor = self.env['ai_digitization.processor'].create({
            'template_id': self.id,
            'document': self.test_document,
            'document_filename': self.test_document_filename,
        })
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Document Processor',
            'view_mode': 'form',
            'res_model': 'ai_digitization.processor',
            'res_id': processor.id,
            'target': 'current',
        }
    
    def _process_document_with_ai(self, document_binary, document_filename, document_mimetype):
        """Process a document using the Gemini AI API and return extracted JSON data"""
        if not self.api_key:
            raise ValueError("API Key is required to process documents")
        
        if not document_binary:
            raise ValueError("No document provided for processing")
        
        # Validate MIME type - Gemini only supports specific types
        supported_mime_types = [
            'application/pdf',
            'image/jpeg',
            'image/png', 
            'image/webp',
            'image/tiff',
            'image/gif'
        ]
        
        # If no MIME type or unsupported type, try to determine from filename
        if not document_mimetype or document_mimetype not in supported_mime_types:
            if document_filename:
                filename = document_filename.lower()
                if filename.endswith('.pdf'):
                    document_mimetype = 'application/pdf'
                elif filename.endswith(('.jpg', '.jpeg')):
                    document_mimetype = 'image/jpeg'
                elif filename.endswith('.png'):
                    document_mimetype = 'image/png'
                elif filename.endswith('.webp'):
                    document_mimetype = 'image/webp'
                elif filename.endswith(('.tiff', '.tif')):
                    document_mimetype = 'image/tiff'
                elif filename.endswith('.gif'):
                    document_mimetype = 'image/gif'
                else:
                    # Default to PNG for unknown image files
                    document_mimetype = 'image/png'
            else:
                # If no filename, default to PNG
                document_mimetype = 'image/png'
        
        # Final validation
        if document_mimetype not in supported_mime_types:
            raise ValueError(f"Unsupported file type: {document_mimetype}. Supported types: {', '.join(supported_mime_types)}")
        
        # Prepare the API request
        api_url = f"https://generativelanguage.googleapis.com/v1/models/{self.ai_model}:generateContent"
        headers = {
            "Content-Type": "application/json"
        }
        
        # Get the final prompt (either predefined template or custom)
        base_prompt = self.final_prompt
        
        # Add field mapping instructions if available
        field_instructions = ""
        if self.field_mappings:
            field_descriptions = []
            for mapping in self.field_mappings:
                field_desc = f"- {mapping.label}"
                if mapping.example_value:
                    field_desc += f" (example: {mapping.example_value})"
                field_descriptions.append(field_desc)
            
            field_instructions = f"\n\nPlease ensure the JSON contains these specific fields:\n" + "\n".join(field_descriptions)
        
        # Combine base prompt with field instructions
        final_prompt = base_prompt + field_instructions + "\n\nReturn only valid JSON format."
        
        # Encode document for API request
        document_data = base64.b64decode(document_binary)
        document_base64 = base64.b64encode(document_data).decode('utf-8')
        
        payload = {
            "contents": [{
                "parts": [
                    {"text": final_prompt},
                    {
                        "inline_data": {
                            "mime_type": document_mimetype,
                            "data": document_base64
                        }
                    }
                ]
            }],
            "generationConfig": {
                "temperature": 0.1,
                "topP": 0.95,
                "topK": 40,
                "maxOutputTokens": 8192
            }
        }
        
        # Add API key to URL as parameter (Gemini API requirement)
        api_url_with_key = f"{api_url}?key={self.api_key}"
        
        # Make the API request
        response = requests.post(api_url_with_key, headers=headers, json=payload)
        
        if response.status_code == 200:
            response_data = response.json()
            # Extract the text response from Gemini
            if 'candidates' in response_data and response_data['candidates']:
                candidate = response_data['candidates'][0]
                if 'content' in candidate and 'parts' in candidate['content']:
                    for part in candidate['content']['parts']:
                        if 'text' in part:
                            text = part['text'].strip()
                            # Try to extract JSON from the response
                            try:
                                # Look for JSON between triple backticks
                                import re
                                json_match = re.search(r'```json\s*([\s\S]*?)\s*```', text)
                                if json_match:
                                    json_text = json_match.group(1).strip()
                                    # Validate JSON
                                    parsed_json = json.loads(json_text)
                                    return parsed_json
                                
                                # If no backticks, try to parse the whole text as JSON
                                parsed_json = json.loads(text)
                                return parsed_json
                            except json.JSONDecodeError:
                                # If not valid JSON, try to extract JSON-like content
                                json_match = re.search(r'\{.*\}', text, re.DOTALL)
                                if json_match:
                                    potential_json = json_match.group(0)
                                    try:
                                        parsed_json = json.loads(potential_json)
                                        return parsed_json
                                    except json.JSONDecodeError:
                                        pass
                                # Return raw text if no valid JSON found
                                return {"extracted_text": text, "raw_response": True}
            raise ValueError("No valid response content found in API response")
        else:
            error_msg = f"API request failed with status code {response.status_code}"
            if response.text:
                try:
                    error_data = json.loads(response.text)
                    if 'error' in error_data:
                        error_msg += f": {error_data['error'].get('message', response.text)}"
                    else:
                        error_msg += f": {response.text}"
                except json.JSONDecodeError:
                    error_msg += f": {response.text}"
            raise ValueError(error_msg)

class AIDigitizationFieldMapping(models.Model):
    _name = 'ai_digitization.field.mapping'
    _description = 'AI Digitization Field Mapping'

    template_id = fields.Many2one('ai_digitization.template', string='Template', ondelete='cascade')
    field_type = fields.Selection([
        ('simple', 'Simple'),
        ('relational', 'Relational'),
        ('extra', 'Extra Field')
    ], string='Field Type', required=True, default='simple')
    target_field_id = fields.Many2one('ir.model.fields', string='Target Field')
    label = fields.Char('JSON Label', required=True)
    example_value = fields.Char('Example Value')
    default_value = fields.Char('Default Value')
    ai_fetch = fields.Boolean('AI Fetch', default=True)
    
class AIDigitizationProcessor(models.Model):
    _name = 'ai_digitization.processor'
    _description = 'AI Digitization Processor'

    name = fields.Char('Name', compute='_compute_name')
    template_id = fields.Many2one('ai_digitization.template', string='Template', required=True)
    document = fields.Binary('Document', required=True, attachment=True)
    document_filename = fields.Char('Filename')
    document_mimetype = fields.Char('MIME Type', compute='_compute_mimetype')
    extracted_data = fields.Text('Extracted JSON', readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('processing', 'Processing'),
        ('done', 'Completed'),
        ('error', 'Error')
    ], string='Status', default='draft')
    record_id = fields.Integer('Created Record ID')
    record_model = fields.Char('Record Model')
    error_message = fields.Text('Error Message')
    
    @api.depends('document_filename', 'template_id')
    def _compute_name(self):
        for record in self:
            if record.document_filename:
                record.name = f"{record.template_id.name or 'Untitled'} - {record.document_filename}"
            else:
                record.name = record.template_id.name or 'Untitled'
                
    @api.depends('document')
    def _compute_mimetype(self):
        for record in self:
            if record.document_filename:
                filename = record.document_filename.lower()
                if filename.endswith('.pdf'):
                    record.document_mimetype = 'application/pdf'
                elif filename.endswith(('.jpg', '.jpeg')):
                    record.document_mimetype = 'image/jpeg'
                elif filename.endswith('.png'):
                    record.document_mimetype = 'image/png'
                elif filename.endswith(('.tiff', '.tif')):
                    record.document_mimetype = 'image/tiff'
                elif filename.endswith('.webp'):
                    record.document_mimetype = 'image/webp'
                elif filename.endswith('.gif'):
                    record.document_mimetype = 'image/gif'
                else:
                    # Default to PNG for unknown image types
                    record.document_mimetype = 'image/png'
            else:
                record.document_mimetype = 'image/png'
    
    def process_document(self):
        self.ensure_one()
        self.state = 'processing'
        try:
            # Call the Gemini API to process the document
            extracted_json = self._call_gemini_api()
            self.extracted_data = extracted_json
            
            # Create a record in the target model using the extracted data
            if extracted_json:
                record_id = self._create_target_record(json.loads(extracted_json))
                if record_id:
                    self.record_id = record_id
                    self.record_model = self.template_id.model_name
                    self.state = 'done'
                else:
                    self.state = 'error'
                    self.error_message = "Failed to create record from extracted data"
            else:
                self.state = 'error'
                self.error_message = "No data extracted from document"
        except Exception as e:
            self.state = 'error'
            self.error_message = str(e)
            _logger.exception("Error processing document with AI digitization: %s", e)
    
    def _call_gemini_api(self):
        """Call the Gemini API to extract data from the document"""
        if not self.template_id.api_key:
            raise ValueError("API Key is required to process documents")
        
        # Validate MIME type - Gemini only supports specific types
        supported_mime_types = [
            'application/pdf',
            'image/jpeg',
            'image/png', 
            'image/webp',
            'image/tiff',
            'image/gif'
        ]
        
        if self.document_mimetype not in supported_mime_types:
            raise ValueError(f"Unsupported file type: {self.document_mimetype}. Supported types: {', '.join(supported_mime_types)}")
            
        # Prepare the API request
        api_url = f"https://generativelanguage.googleapis.com/v1/models/{self.template_id.ai_model}:generateContent"
        headers = {
            "Content-Type": "application/json"
        }
        
        # Get the final prompt (either predefined template or custom)
        base_prompt = self.template_id.final_prompt
        
        # Add field mapping instructions if available
        field_instructions = ""
        if self.template_id.field_mappings:
            field_descriptions = []
            for mapping in self.template_id.field_mappings:
                field_desc = f"- {mapping.label}"
                if mapping.example_value:
                    field_desc += f" (example: {mapping.example_value})"
                field_descriptions.append(field_desc)
            
            field_instructions = f"\n\nPlease ensure the JSON contains these specific fields:\n" + "\n".join(field_descriptions)
        
        # Combine base prompt with field instructions
        final_prompt = base_prompt + field_instructions + "\n\nReturn only valid JSON format."
        
        # Encode document for API request
        if self.document:
            document_data = base64.b64decode(self.document)
            document_base64 = base64.b64encode(document_data).decode('utf-8')
            
            payload = {
                "contents": [{
                    "parts": [
                        {"text": final_prompt},
                        {
                            "inline_data": {
                                "mime_type": self.document_mimetype,
                                "data": document_base64
                            }
                        }
                    ]
                }],
                "generationConfig": {
                    "temperature": 0.1,
                    "topP": 0.95,
                    "topK": 40,
                    "maxOutputTokens": 8192
                }
            }
            
            # Add API key to URL as parameter (Gemini API requirement)
            api_url_with_key = f"{api_url}?key={self.template_id.api_key}"
            
            # Make the API request
            response = requests.post(api_url_with_key, headers=headers, json=payload)
            
            if response.status_code == 200:
                response_data = response.json()
                # Extract the text response from Gemini
                if 'candidates' in response_data and response_data['candidates']:
                    candidate = response_data['candidates'][0]
                    if 'content' in candidate and 'parts' in candidate['content']:
                        for part in candidate['content']['parts']:
                            if 'text' in part:
                                text = part['text'].strip()
                                # Try to extract JSON from the response
                                try:
                                    # Look for JSON between triple backticks
                                    import re
                                    json_match = re.search(r'```json\s*([\s\S]*?)\s*```', text)
                                    if json_match:
                                        json_text = json_match.group(1).strip()
                                        # Validate JSON
                                        json.loads(json_text)
                                        return json_text
                                    
                                    # If no backticks, try to parse the whole text as JSON
                                    json.loads(text)
                                    return text
                                except json.JSONDecodeError:
                                    # If not valid JSON, try to extract JSON-like content
                                    json_match = re.search(r'\{.*\}', text, re.DOTALL)
                                    if json_match:
                                        potential_json = json_match.group(0)
                                        try:
                                            json.loads(potential_json)
                                            return potential_json
                                        except json.JSONDecodeError:
                                            pass
                                    # Return raw text if no valid JSON found
                                    escaped_text = text.replace('"', '\\"')
                                    return f'{{"extracted_text": "{escaped_text}"}}'
                raise ValueError("No valid response content found in API response")
            else:
                error_msg = f"API request failed with status code {response.status_code}"
                if response.text:
                    error_msg += f": {response.text}"
                raise ValueError(error_msg)
        else:
            raise ValueError("No document provided for processing")
    
    def _create_target_record(self, extracted_data):
        """Create a record in the target model using the extracted JSON data"""
        if not extracted_data or not self.template_id.model_name:
            return False
            
        # Get the model
        model = self.env[self.template_id.model_name]
        
        # Prepare the values for creating the record
        values = {}
        for mapping in self.template_id.field_mappings:
            field_name = mapping.target_field_id.name if mapping.target_field_id else None
            json_key = mapping.label
            
            if not field_name:
                continue
                
            # Try to get the value from the extracted data
            value = None
            if json_key in extracted_data:
                value = extracted_data[json_key]
            elif mapping.default_value:
                value = mapping.default_value
            
            if value is not None:
                values[field_name] = value
                
        # Create the record if we have values
        if values:
            try:
                record = model.create(values)
                return record.id
            except Exception as e:
                _logger.exception("Failed to create record from extracted data: %s", e)
                return False
        
        return False
