# AI Document Extraction Module for Odoo

## Overview

The `ai_document_extraction` module provides a robust framework for extracting structured data from documents (PDFs, images, etc.) using AI capabilities in Odoo. This module defines a reusable mixin that can be injected into any model to enable automatic AI document extraction when documents are uploaded or attached.

## Features

- **Document Data Extraction**: Extract structured data from PDF documents, images, and more
- **AI Integration**: Leverages the Odoo AI module for document analysis and extraction
- **Extensible Architecture**: Easy to extend to new document types and models
- **Custom AI Agent Support**: Includes extended support for Gemini 2.0 Flash model
- **Error Handling**: Robust error handling and reporting
- **User-Friendly Interface**: Simple UI for triggering extractions and viewing results

## Technical Information

### Module Dependencies

- `base`: Odoo base module
- `mail`: For attachment and message functionality
- `hr`: For employee model integration
- `ai`: Odoo AI module for integration with AI services

### Installation

1. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Install the module in Odoo:
   - Place the module in your Odoo addons directory
   - Update the module list in Odoo
   - Install the module through the Odoo Apps interface

### Configuration

1. **AI Configuration**:
   - Configure an AI agent in Odoo (Settings → AI → Agents)
   - Ensure API keys are properly set for your AI provider (Google, OpenAI, etc.)

2. **Model Integration**:
   - Any model that needs document extraction capabilities should inherit from `ai.document.mixin`
   - Implement the required methods as shown in the example models

## Usage

### Basic Usage

1. Attach a document to a record that uses the AI document extraction mixin
2. Select an AI agent for extraction
3. Click the "Extract Document" button
4. View the extracted data in the JSON field or the mapped fields

### Extending to New Models

To add document extraction capabilities to a new model:

1. Inherit from `ai.document.mixin` in your model definition:
   ```python
   class YourModel(models.Model):
       _name = 'your.model'
       _inherit = ['your.model', 'ai.document.mixin']
       _description = 'Your Model with AI Document Extraction'
   ```

2. Implement the required methods:
   ```python
   def _map_ai_extracted_data(self, extracted_data):
       """Map extracted JSON data to model fields"""
       # Implement your mapping logic here
       return True
       
   def _get_document_type_name(self):
       """Return document type for extraction prompt"""
       return "Your Document Type"
   ```

## Key Components

### Mixins

- **AIDocumentMixin**: Core mixin that provides document extraction capabilities
- **DateTimeEncoder**: Custom JSON encoder for handling datetime objects in extraction results

### Models

- **ai.agent**: Extended to support Gemini 2.0 Flash for document extraction
- **hr.employee**: Example implementation showing integration with the Employee model

## Technical Notes

- The module handles various document formats including PDFs, images, and text files
- Extracted data is stored in JSON format for flexibility
- The extraction process uses AI to interpret document content and convert it to structured data
- All extraction attempts are logged for troubleshooting

## Support & Maintenance

For issues, feature requests, or contributions, please contact the module maintainer or submit to the repository.

## License

LGPL-3

---

*This module was developed to provide a flexible framework for AI-powered document extraction in Odoo.*
