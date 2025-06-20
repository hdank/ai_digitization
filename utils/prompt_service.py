# -*- coding: utf-8 -*-

class PromptService:
    """Service class for generating AI prompts based on agent configuration"""
    
    @staticmethod
    def generate_system_prompt(system_prompt, context_info, file_info):
        """Generate prompt using the agent's system prompt"""
        prompt = f"""{system_prompt}

{context_info}

Document: {file_info['filename']}"""
        
        # Add document content if available
        if file_info.get('content'):
            prompt += f"""

Document content:
{file_info['content']}"""

        return prompt

    @staticmethod
    def generate_document_extraction_prompt(context_info, file_info):
        """Generate specialized document extraction prompt"""
        prompt = f"""You are a professional data extraction specialist working with Odoo ERP system.

{context_info}

Document: {file_info['filename']}"""
        
        # Add document content if available
        if file_info.get('content'):
            prompt += f"""

Document content:
{file_info['content']}"""
        
        prompt += """

Please analyze this document and extract structured information in JSON format that would be relevant for this Odoo record.

Requirements:
- Return ONLY valid JSON format
- Use descriptive field names that could map to Odoo fields
- Group related information logically
- If information is not found, use null or empty values
- Focus on data that would be useful for the specified Odoo model

Extract key information such as:
- Document metadata (type, title, date, etc.)
- Contact information (names, emails, phones, addresses)
- Financial data (amounts, dates, currencies)
- Any structured data relevant to the Odoo model
- Main content summary"""
        
        return prompt

    @staticmethod
    def generate_basic_analysis_prompt(context_info, file_info):
        """Generate basic analysis prompt for regular agents"""
        prompt = f"""Extract information from this document: {file_info['filename']}

Context: {context_info}"""
        
        # Add document content if available
        if file_info.get('content'):
            prompt += f"""

Document content:
{file_info['content']}"""
        
        prompt += """

Please extract relevant information and return it in a clear and structured format."""
        
        return prompt

    @classmethod
    def generate_prompt_for_file(cls, agent, context_info, file_info):
        """Generate appropriate prompt based on agent configuration"""
        if agent.is_document_extraction:
            return cls.generate_document_extraction_prompt(context_info, file_info)
        elif agent.system_prompt:
            return cls.generate_system_prompt(agent.system_prompt, context_info, file_info)
        else:
            return cls.generate_basic_analysis_prompt(context_info, file_info)
