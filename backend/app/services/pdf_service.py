"""
PDF Generation Service for Digital Articles.

This service creates professional PDF documents from notebook data,
including methodologies, results, plots, and tables in a scientific article format.
"""

import base64
import io
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

import markdown
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle,
    PageBreak, KeepTogether
)
from reportlab.platypus.flowables import HRFlowable
from PIL import Image as PILImage

from ..models.notebook import Notebook, Cell, CellType

logger = logging.getLogger(__name__)


class PDFService:
    """Service for generating PDF documents from digital articles."""
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Set up custom paragraph styles for the PDF."""
        # Title style
        self.styles.add(ParagraphStyle(
            name='ArticleTitle',
            parent=self.styles['Title'],
            fontSize=24,
            spaceAfter=12,
            alignment=1,  # Center alignment
            textColor=colors.HexColor('#2563eb')
        ))
        
        # Subtitle style
        self.styles.add(ParagraphStyle(
            name='ArticleSubtitle',
            parent=self.styles['Normal'],
            fontSize=14,
            spaceAfter=20,
            alignment=1,  # Center alignment
            textColor=colors.HexColor('#6b7280'),
            fontName='Helvetica-Oblique'
        ))
        
        # Section heading style
        self.styles.add(ParagraphStyle(
            name='SectionHeading',
            parent=self.styles['Heading2'],
            fontSize=16,
            spaceBefore=20,
            spaceAfter=10,
            textColor=colors.HexColor('#1f2937'),
            borderWidth=1,
            borderColor=colors.HexColor('#e5e7eb'),
            borderPadding=8,
            backColor=colors.HexColor('#f9fafb')
        ))
        
        # Methodology style
        self.styles.add(ParagraphStyle(
            name='Methodology',
            parent=self.styles['Normal'],
            fontSize=11,
            spaceBefore=8,
            spaceAfter=12,
            leftIndent=20,
            rightIndent=20,
            backColor=colors.HexColor('#f0f9ff'),
            borderWidth=1,
            borderColor=colors.HexColor('#0ea5e9'),
            borderPadding=10,
            fontName='Helvetica-Oblique'
        ))
        
        # Code style
        self.styles.add(ParagraphStyle(
            name='CustomCode',
            parent=self.styles['Code'],
            fontSize=9,
            spaceBefore=8,
            spaceAfter=8,
            leftIndent=20,
            rightIndent=20,
            backColor=colors.HexColor('#f8fafc'),
            borderWidth=1,
            borderColor=colors.HexColor('#cbd5e1'),
            borderPadding=8,
            fontName='Courier'
        ))
        
        # Results style
        self.styles.add(ParagraphStyle(
            name='Results',
            parent=self.styles['Normal'],
            fontSize=11,
            spaceBefore=8,
            spaceAfter=12,
            leftIndent=10,
            rightIndent=10
        ))
    
    def generate_pdf(self, notebook: Notebook, include_code: bool = False) -> bytes:
        """
        Generate a PDF document from a notebook.
        
        Args:
            notebook: The notebook to convert to PDF
            include_code: Whether to include generated code in the PDF
            
        Returns:
            PDF content as bytes
        """
        logger.info(f"Generating PDF for notebook: {notebook.title}")
        
        # Create PDF buffer
        buffer = io.BytesIO()
        
        # Create document
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )
        
        # Build document content
        story = []
        
        # Add title page
        self._add_title_page(story, notebook)
        
        # Add cells
        for i, cell in enumerate(notebook.cells):
            if cell.cell_type in (CellType.PROMPT, CellType.CODE, CellType.METHODOLOGY):
                self._add_cell_content(story, cell, i + 1, include_code)
        
        # Build PDF
        doc.build(story)
        
        # Get PDF bytes
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        logger.info(f"PDF generated successfully: {len(pdf_bytes)} bytes")
        return pdf_bytes
    
    def _add_title_page(self, story: List, notebook: Notebook):
        """Add title page to the PDF."""
        # Title
        title = Paragraph(notebook.title, self.styles['ArticleTitle'])
        story.append(title)
        story.append(Spacer(1, 12))
        
        # Subtitle/Description
        if notebook.description:
            subtitle = Paragraph(notebook.description, self.styles['ArticleSubtitle'])
            story.append(subtitle)
            story.append(Spacer(1, 20))
        
        # Metadata table
        metadata = [
            ['Author:', notebook.author],
            ['Created:', notebook.created_at.strftime('%B %d, %Y')],
            ['Last Updated:', notebook.updated_at.strftime('%B %d, %Y at %I:%M %p')],
            ['Total Cells:', str(len(notebook.cells))],
            ['LLM Model:', f"{notebook.llm_provider}/{notebook.llm_model}"]
        ]
        
        metadata_table = Table(metadata, colWidths=[2*inch, 4*inch])
        metadata_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e5e7eb')),
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f9fafb')),
            ('PADDING', (0, 0), (-1, -1), 8),
        ]))
        
        story.append(metadata_table)
        story.append(Spacer(1, 30))
        
        # Horizontal line
        story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#2563eb')))
        story.append(PageBreak())
    
    def _add_cell_content(self, story: List, cell: Cell, cell_number: int, include_code: bool):
        """Add a cell's content to the PDF."""
        # Cell section heading
        if cell.prompt:
            heading_text = f"{cell_number}. {cell.prompt}"
        else:
            heading_text = f"{cell_number}. Cell {cell.id}"
        
        heading = Paragraph(heading_text, self.styles['SectionHeading'])
        story.append(KeepTogether([heading, Spacer(1, 10)]))
        
        # Scientific methodology (if available)
        if cell.scientific_explanation:
            methodology_title = Paragraph("<b>Scientific Methodology:</b>", self.styles['Normal'])
            story.append(methodology_title)
            
            # Convert markdown to HTML if needed
            methodology_text = self._process_text(cell.scientific_explanation)
            methodology = Paragraph(methodology_text, self.styles['Methodology'])
            story.append(methodology)
            story.append(Spacer(1, 10))
        
        # Generated code (optional)
        if include_code and cell.code:
            code_title = Paragraph("<b>Generated Code:</b>", self.styles['Normal'])
            story.append(code_title)
            
            # Format code with line breaks
            formatted_code = cell.code.replace('\n', '<br/>')
            code_para = Paragraph(formatted_code, self.styles['CustomCode'])
            story.append(code_para)
            story.append(Spacer(1, 10))
        
        # Results
        if cell.last_result:
            results_title = Paragraph("<b>Results:</b>", self.styles['Normal'])
            story.append(results_title)
            
            # Add text output
            if cell.last_result.stdout:
                output_text = self._process_text(cell.last_result.stdout)
                output_para = Paragraph(f"<font name='Courier'>{output_text}</font>", self.styles['Results'])
                story.append(output_para)
                story.append(Spacer(1, 8))
            
            # Add plots
            if cell.last_result.plots:
                self._add_plots(story, cell.last_result.plots)
            
            # Add interactive plots (as static images)
            if cell.last_result.interactive_plots:
                self._add_interactive_plots(story, cell.last_result.interactive_plots)
            
            # Add tables
            if cell.last_result.tables:
                self._add_tables(story, cell.last_result.tables)
        
        # Add separator between cells
        story.append(Spacer(1, 20))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#e5e7eb')))
        story.append(Spacer(1, 20))
    
    def _add_plots(self, story: List, plots: List[str]):
        """Add matplotlib plots to the PDF."""
        for i, plot_b64 in enumerate(plots):
            try:
                # Decode base64 image
                image_data = base64.b64decode(plot_b64)
                image_buffer = io.BytesIO(image_data)
                
                # Create PIL image to get dimensions
                pil_img = PILImage.open(image_buffer)
                img_width, img_height = pil_img.size
                
                # Calculate scaled dimensions (max width: 6 inches)
                max_width = 6 * inch
                if img_width > max_width:
                    scale_factor = max_width / img_width
                    scaled_width = max_width
                    scaled_height = img_height * scale_factor
                else:
                    scaled_width = img_width
                    scaled_height = img_height
                
                # Reset buffer position
                image_buffer.seek(0)
                
                # Create ReportLab image
                img = Image(image_buffer, width=scaled_width, height=scaled_height)
                story.append(img)
                story.append(Spacer(1, 10))
                
            except Exception as e:
                logger.warning(f"Failed to add plot {i}: {e}")
                error_text = Paragraph(f"[Plot {i+1}: Error loading image]", self.styles['Results'])
                story.append(error_text)
    
    def _add_interactive_plots(self, story: List, interactive_plots: List[Dict[str, Any]]):
        """Add interactive plots as static images to the PDF."""
        for i, plot_data in enumerate(interactive_plots):
            try:
                plot_title = Paragraph(f"<b>Interactive Plot: {plot_data.get('name', f'Plot {i+1}')}</b>", 
                                     self.styles['Results'])
                story.append(plot_title)
                
                # Note about interactivity
                note = Paragraph(
                    "<i>Note: This is a static representation of an interactive plot. "
                    "View the original digital article for full interactivity.</i>",
                    self.styles['Results']
                )
                story.append(note)
                story.append(Spacer(1, 10))
                
            except Exception as e:
                logger.warning(f"Failed to add interactive plot {i}: {e}")
    
    def _add_tables(self, story: List, tables: List[Dict[str, Any]]):
        """Add tables to the PDF."""
        for table_data in tables:
            try:
                table_name = table_data.get('name', 'Table')
                table_title = Paragraph(f"<b>Table: {table_name}</b>", self.styles['Results'])
                story.append(table_title)
                
                # Get table info
                shape = table_data.get('shape', [0, 0])
                columns = table_data.get('columns', [])
                data = table_data.get('data', [])
                
                # Create table info
                info_text = f"Shape: {shape[0]} rows × {shape[1]} columns"
                info_para = Paragraph(info_text, self.styles['Results'])
                story.append(info_para)
                story.append(Spacer(1, 5))
                
                # Create table (show first 10 rows max)
                if data and columns:
                    # Prepare table data
                    table_rows = [columns]  # Header row
                    
                    # Add data rows (limit to first 10)
                    for i, row in enumerate(data[:10]):
                        if isinstance(row, dict):
                            table_row = [str(row.get(col, '')) for col in columns]
                        else:
                            table_row = [str(val) for val in row]
                        table_rows.append(table_row)
                    
                    # Create ReportLab table
                    pdf_table = Table(table_rows)
                    pdf_table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f3f4f6')),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#1f2937')),
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, 0), 10),
                        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                        ('FONTSIZE', (0, 1), (-1, -1), 8),
                        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#d1d5db')),
                    ]))
                    
                    story.append(pdf_table)
                    
                    # Add note if table was truncated
                    if len(data) > 10:
                        truncate_note = Paragraph(
                            f"<i>Note: Showing first 10 rows of {len(data)} total rows.</i>",
                            self.styles['Results']
                        )
                        story.append(truncate_note)
                
                story.append(Spacer(1, 15))
                
            except Exception as e:
                logger.warning(f"Failed to add table: {e}")
                error_text = Paragraph(f"[Table: Error loading data]", self.styles['Results'])
                story.append(error_text)
    
    def _process_text(self, text: str) -> str:
        """Process text for PDF display, handling special characters and formatting."""
        if not text:
            return ""
        
        # Escape HTML special characters
        text = text.replace('&', '&amp;')
        text = text.replace('<', '&lt;')
        text = text.replace('>', '&gt;')
        
        # Convert line breaks to HTML breaks
        text = text.replace('\n', '<br/>')
        
        # Limit length for display
        if len(text) > 2000:
            text = text[:2000] + "...<br/><i>[Content truncated for PDF display]</i>"
        
        return text
