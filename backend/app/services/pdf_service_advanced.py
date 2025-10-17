"""
Advanced PDF Generation Service for Scientific Digital Articles.

This service creates publication-quality PDF documents with professional
scientific article formatting, including proper typography, layout, and
visual elements optimized for academic and research contexts.
"""

import base64
import io
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple

import markdown
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm, mm
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, 
    KeepTogether, PageBreak
)
from reportlab.platypus.flowables import HRFlowable, Flowable
from PIL import Image as PILImage

from ..models.notebook import Notebook, Cell, CellType

logger = logging.getLogger(__name__)


class SectionBreak(Flowable):
    """Custom flowable for section breaks."""
    
    def __init__(self, width=None):
        Flowable.__init__(self)
        self.width = width or 15*cm
        self.height = 0.5*cm
        
    def draw(self):
        self.canv.setStrokeColor(colors.HexColor('#2563eb'))
        self.canv.setLineWidth(2)
        self.canv.line(0, self.height/2, self.width, self.height/2)


class AdvancedPDFService:
    """Advanced service for generating publication-quality PDF documents."""
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_advanced_styles()
        
    def _setup_advanced_styles(self):
        """Set up professional typography styles for scientific articles."""
        
        # Title style - Large, bold, centered
        self.styles.add(ParagraphStyle(
            name='ArticleTitle',
            parent=self.styles['Title'],
            fontSize=20,
            spaceAfter=6,
            spaceBefore=12,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#1a202c'),
            fontName='Helvetica-Bold',
            leading=24
        ))
        
        # Subtitle style - Elegant, centered
        self.styles.add(ParagraphStyle(
            name='ArticleSubtitle',
            parent=self.styles['Normal'],
            fontSize=12,
            spaceAfter=18,
            spaceBefore=6,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#4a5568'),
            fontName='Helvetica-Oblique',
            leading=15
        ))
        
        # Author and metadata style
        self.styles.add(ParagraphStyle(
            name='AuthorInfo',
            parent=self.styles['Normal'],
            fontSize=10,
            spaceAfter=24,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#2d3748'),
            fontName='Helvetica',
            leading=12
        ))
        
        # Abstract style
        self.styles.add(ParagraphStyle(
            name='Abstract',
            parent=self.styles['Normal'],
            fontSize=10,
            spaceBefore=12,
            spaceAfter=18,
            leftIndent=1*cm,
            rightIndent=1*cm,
            alignment=TA_JUSTIFY,
            fontName='Helvetica',
            leading=12,
            backColor=colors.HexColor('#f7fafc'),
            borderWidth=0.5,
            borderColor=colors.HexColor('#e2e8f0'),
            borderPadding=12
        ))
        
        # Section heading style - Professional hierarchy
        self.styles.add(ParagraphStyle(
            name='SectionHeading',
            parent=self.styles['Heading1'],
            fontSize=14,
            spaceBefore=18,
            spaceAfter=12,
            textColor=colors.HexColor('#2b6cb0'),
            fontName='Helvetica-Bold',
            leading=16,
            borderWidth=0,
            borderPadding=0
        ))
        
        # Subsection heading
        self.styles.add(ParagraphStyle(
            name='SubsectionHeading',
            parent=self.styles['Heading2'],
            fontSize=12,
            spaceBefore=14,
            spaceAfter=8,
            textColor=colors.HexColor('#2d3748'),
            fontName='Helvetica-Bold',
            leading=14
        ))
        
        # Methodology style - Highlighted scientific content
        self.styles.add(ParagraphStyle(
            name='Methodology',
            parent=self.styles['Normal'],
            fontSize=10,
            spaceBefore=8,
            spaceAfter=12,
            leftIndent=0,
            rightIndent=0,
            alignment=TA_JUSTIFY,
            backColor=colors.HexColor('#edf2f7'),
            borderWidth=0.5,
            borderColor=colors.HexColor('#4299e1'),
            borderPadding=10,
            fontName='Helvetica',
            leading=12
        ))
        
        # Code style - Monospace with proper formatting
        self.styles.add(ParagraphStyle(
            name='ScientificCode',
            parent=self.styles['Code'],
            fontSize=8,
            spaceBefore=8,
            spaceAfter=8,
            leftIndent=0,
            rightIndent=0,
            backColor=colors.HexColor('#f8f9fa'),
            borderWidth=0.5,
            borderColor=colors.HexColor('#dee2e6'),
            borderPadding=8,
            fontName='Courier',
            leading=10
        ))
        
        # Results text style
        self.styles.add(ParagraphStyle(
            name='Results',
            parent=self.styles['Normal'],
            fontSize=10,
            spaceBefore=6,
            spaceAfter=8,
            alignment=TA_JUSTIFY,
            fontName='Helvetica',
            leading=12
        ))
        
        # Caption style for figures and tables
        self.styles.add(ParagraphStyle(
            name='Caption',
            parent=self.styles['Normal'],
            fontSize=9,
            spaceBefore=4,
            spaceAfter=12,
            alignment=TA_JUSTIFY,
            fontName='Helvetica-Oblique',
            textColor=colors.HexColor('#4a5568'),
            leading=11
        ))
        
        # Table header style
        self.styles.add(ParagraphStyle(
            name='TableHeader',
            parent=self.styles['Normal'],
            fontSize=9,
            fontName='Helvetica-Bold',
            textColor=colors.HexColor('#2d3748'),
            alignment=TA_CENTER
        ))
    
    def generate_pdf(self, notebook: Notebook, include_code: bool = False) -> bytes:
        """
        Generate a publication-quality PDF document from a notebook.
        
        Args:
            notebook: The notebook to convert to PDF
            include_code: Whether to include generated code in the PDF
            
        Returns:
            PDF content as bytes
        """
        logger.info(f"Generating advanced PDF for notebook: {notebook.title}")
        
        # Create PDF buffer
        buffer = io.BytesIO()
        
        # Create document with professional layout
        from reportlab.platypus import SimpleDocTemplate
        
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2.5*cm,
            bottomMargin=2.5*cm,
            title=notebook.title,
            author=notebook.author
        )
        
        # Build document content
        story = []
        
        # Add title page content
        self._add_title_section(story, notebook)
        
        # Add abstract/summary if available
        self._add_abstract_section(story, notebook)
        
        # Add methodology and results sections
        self._add_content_sections(story, notebook, include_code)
        
        # Build PDF
        doc.build(story)
        
        # Get PDF bytes
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        logger.info(f"Advanced PDF generated successfully: {len(pdf_bytes)} bytes")
        return pdf_bytes
    
    def _add_title_section(self, story: List, notebook: Notebook):
        """Add professional title section."""
        # Main title
        title = Paragraph(notebook.title, self.styles['ArticleTitle'])
        story.append(title)
        
        # Subtitle/Description
        if notebook.description:
            subtitle = Paragraph(notebook.description, self.styles['ArticleSubtitle'])
            story.append(subtitle)
        
        # Author and metadata
        author_info = f"""
        <b>{notebook.author}</b><br/>
        Generated on {notebook.updated_at.strftime('%B %d, %Y')}<br/>
        Digital Article System • {notebook.llm_provider}/{notebook.llm_model}
        """
        author_para = Paragraph(author_info, self.styles['AuthorInfo'])
        story.append(author_para)
        
        # Add some space before content
        story.append(Spacer(1, 12))
        story.append(SectionBreak())
        story.append(Spacer(1, 18))
    
    def _add_abstract_section(self, story: List, notebook: Notebook):
        """Add abstract section if we can generate one from the content."""
        # Generate a brief abstract from the notebook content
        if notebook.cells:
            abstract_text = self._generate_abstract(notebook)
            if abstract_text:
                # Abstract heading
                abstract_heading = Paragraph("<b>Abstract</b>", self.styles['SectionHeading'])
                story.append(abstract_heading)
                
                # Abstract content
                abstract_para = Paragraph(abstract_text, self.styles['Abstract'])
                story.append(abstract_para)
                
                story.append(Spacer(1, 18))
    
    def _generate_abstract(self, notebook: Notebook) -> str:
        """Generate an abstract from notebook content."""
        prompts = []
        methodologies = []
        
        for cell in notebook.cells[:3]:  # Use first 3 cells for abstract
            if cell.prompt:
                prompts.append(cell.prompt)
            if cell.scientific_explanation:
                methodologies.append(cell.scientific_explanation[:200])
        
        if not prompts:
            return ""
        
        abstract_parts = []
        if prompts:
            abstract_parts.append(f"This digital article presents an analysis involving {', '.join(prompts[:2])}.")
        
        if methodologies:
            abstract_parts.append("The methodology encompasses computational approaches for data analysis and visualization.")
        
        abstract_parts.append(f"Results are presented through {len(notebook.cells)} analytical components with integrated visualizations and statistical outputs.")
        
        return " ".join(abstract_parts)
    
    def _add_content_sections(self, story: List, notebook: Notebook, include_code: bool):
        """Add the main content sections with proper scientific structure."""
        
        # Group cells by type for better organization
        methodology_cells = []
        analysis_cells = []
        
        for cell in notebook.cells:
            if cell.cell_type in (CellType.PROMPT, CellType.CODE, CellType.METHODOLOGY):
                if cell.scientific_explanation:
                    methodology_cells.append(cell)
                else:
                    analysis_cells.append(cell)
        
        # Methodology section
        if methodology_cells:
            self._add_methodology_section(story, methodology_cells, include_code)
        
        # Results and Analysis section
        if notebook.cells:
            self._add_results_section(story, notebook.cells, include_code)
    
    def _add_methodology_section(self, story: List, cells: List[Cell], include_code: bool):
        """Add methodology section with scientific explanations."""
        # Section heading
        methodology_heading = Paragraph("Methodology", self.styles['SectionHeading'])
        story.append(methodology_heading)
        
        for i, cell in enumerate(cells, 1):
            if cell.scientific_explanation:
                # Subsection for each methodology
                if cell.prompt:
                    subsection_title = f"{i}. {cell.prompt}"
                    subsection = Paragraph(subsection_title, self.styles['SubsectionHeading'])
                    story.append(subsection)
                
                # Methodology content
                methodology_text = self._process_text_for_pdf(cell.scientific_explanation)
                methodology_para = Paragraph(methodology_text, self.styles['Methodology'])
                story.append(methodology_para)
                
                # Optional code block
                if include_code and cell.code:
                    code_title = Paragraph("<b>Implementation:</b>", self.styles['Results'])
                    story.append(code_title)
                    
                    formatted_code = self._format_code_for_pdf(cell.code)
                    code_para = Paragraph(formatted_code, self.styles['ScientificCode'])
                    story.append(code_para)
                
                story.append(Spacer(1, 12))
    
    def _add_results_section(self, story: List, cells: List[Cell], include_code: bool):
        """Add results section with outputs and visualizations."""
        # Section heading
        results_heading = Paragraph("Results and Analysis", self.styles['SectionHeading'])
        story.append(results_heading)
        
        figure_counter = 1
        table_counter = 1
        
        for i, cell in enumerate(cells, 1):
            if cell.last_result and (cell.last_result.plots or cell.last_result.tables or 
                                   cell.last_result.interactive_plots or cell.last_result.stdout):
                
                # Subsection heading
                if cell.prompt:
                    subsection_title = f"{i}. {cell.prompt}"
                    subsection = Paragraph(subsection_title, self.styles['SubsectionHeading'])
                    story.append(subsection)
                
                # Add text output if available
                if cell.last_result.stdout:
                    output_text = self._process_text_for_pdf(cell.last_result.stdout)
                    if len(output_text.strip()) > 0:
                        output_para = Paragraph(output_text, self.styles['Results'])
                        story.append(output_para)
                        story.append(Spacer(1, 8))
                
                # Add figures (plots)
                if cell.last_result.plots:
                    for plot_b64 in cell.last_result.plots:
                        figure_counter = self._add_figure(story, plot_b64, figure_counter, cell.prompt)
                
                # Add interactive plots
                if cell.last_result.interactive_plots:
                    for plot_data in cell.last_result.interactive_plots:
                        self._add_interactive_plot_description(story, plot_data, figure_counter)
                        figure_counter += 1
                
                # Add tables
                if cell.last_result.tables:
                    for table_data in cell.last_result.tables:
                        table_counter = self._add_professional_table(story, table_data, table_counter)
                
                story.append(Spacer(1, 16))
    
    def _add_figure(self, story: List, plot_b64: str, figure_num: int, caption_context: str = "") -> int:
        """Add a professionally formatted figure."""
        try:
            # Decode and process image
            image_data = base64.b64decode(plot_b64)
            image_buffer = io.BytesIO(image_data)
            
            # Create PIL image to get dimensions
            pil_img = PILImage.open(image_buffer)
            img_width, img_height = pil_img.size
            
            # Calculate scaled dimensions for optimal layout
            max_width = 15*cm  # Fit within column
            max_height = 12*cm
            
            # Maintain aspect ratio
            scale_factor = min(max_width / img_width, max_height / img_height)
            scaled_width = img_width * scale_factor
            scaled_height = img_height * scale_factor
            
            # Reset buffer position
            image_buffer.seek(0)
            
            # Create ReportLab image
            img = Image(image_buffer, width=scaled_width, height=scaled_height)
            
            # Center the image
            img.hAlign = 'CENTER'
            story.append(img)
            
            # Add professional caption
            caption_text = f"<b>Figure {figure_num}.</b> "
            if caption_context:
                caption_text += f"Analysis results for: {caption_context}"
            else:
                caption_text += "Generated visualization from data analysis."
            
            caption = Paragraph(caption_text, self.styles['Caption'])
            story.append(caption)
            story.append(Spacer(1, 12))
            
            return figure_num + 1
            
        except Exception as e:
            logger.warning(f"Failed to add figure {figure_num}: {e}")
            # Add error placeholder
            error_text = Paragraph(
                f"<b>Figure {figure_num}.</b> [Error loading visualization]",
                self.styles['Caption']
            )
            story.append(error_text)
            return figure_num + 1
    
    def _add_interactive_plot_description(self, story: List, plot_data: Dict, figure_num: int):
        """Add description for interactive plots."""
        plot_name = plot_data.get('name', f'Interactive Plot {figure_num}')
        
        description = Paragraph(
            f"<b>Figure {figure_num}.</b> Interactive visualization: {plot_name}. "
            "This plot contains interactive elements that are available in the digital version.",
            self.styles['Caption']
        )
        story.append(description)
        story.append(Spacer(1, 12))
    
    def _add_professional_table(self, story: List, table_data: Dict, table_num: int) -> int:
        """Add a professionally formatted table."""
        try:
            table_name = table_data.get('name', f'Table {table_num}')
            columns = table_data.get('columns', [])
            data = table_data.get('data', [])
            shape = table_data.get('shape', [0, 0])
            
            if not data or not columns:
                return table_num
            
            # Table caption
            caption_text = f"<b>Table {table_num}.</b> {table_name} (n={shape[0]} observations, {shape[1]} variables)"
            caption = Paragraph(caption_text, self.styles['Caption'])
            story.append(caption)
            story.append(Spacer(1, 6))
            
            # Prepare table data (limit rows for readability)
            max_rows = 15
            table_rows = []
            
            # Header row
            header_row = [Paragraph(f"<b>{col}</b>", self.styles['TableHeader']) for col in columns]
            table_rows.append(header_row)
            
            # Data rows
            display_data = data[:max_rows]
            for row in display_data:
                if isinstance(row, dict):
                    table_row = []
                    for col in columns:
                        value = str(row.get(col, ''))
                        # Truncate long values
                        if len(value) > 20:
                            value = value[:17] + "..."
                        table_row.append(Paragraph(value, self.styles['Normal']))
                    table_rows.append(table_row)
                else:
                    table_row = [Paragraph(str(val)[:20], self.styles['Normal']) for val in row[:len(columns)]]
                    table_rows.append(table_row)
            
            # Create table with professional styling
            pdf_table = Table(table_rows, repeatRows=1)
            
            # Professional table styling
            table_style = TableStyle([
                # Header styling
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f8f9fa')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#2d3748')),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('TOPPADDING', (0, 0), (-1, 0), 8),
                
                # Data styling
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
                ('TOPPADDING', (0, 1), (-1, -1), 4),
                
                # Grid and borders
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
                ('LINEBELOW', (0, 0), (-1, 0), 1, colors.HexColor('#cbd5e0')),
                
                # Alternating row colors
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')])
            ])
            
            pdf_table.setStyle(table_style)
            story.append(pdf_table)
            
            # Add truncation note if needed
            if len(data) > max_rows:
                note = Paragraph(
                    f"<i>Note: Showing first {max_rows} rows of {len(data)} total observations.</i>",
                    self.styles['Caption']
                )
                story.append(note)
            
            story.append(Spacer(1, 16))
            return table_num + 1
            
        except Exception as e:
            logger.warning(f"Failed to add table {table_num}: {e}")
            error_text = Paragraph(
                f"<b>Table {table_num}.</b> [Error loading table data]",
                self.styles['Caption']
            )
            story.append(error_text)
            return table_num + 1
    
    def _process_text_for_pdf(self, text: str) -> str:
        """Process text for optimal PDF display with proper formatting."""
        if not text:
            return ""
        
        # Clean up text
        text = text.strip()
        
        # Escape HTML special characters
        text = text.replace('&', '&amp;')
        text = text.replace('<', '&lt;')
        text = text.replace('>', '&gt;')
        
        # Convert line breaks to proper paragraph breaks
        paragraphs = text.split('\n\n')
        processed_paragraphs = []
        
        for para in paragraphs:
            para = para.replace('\n', ' ').strip()
            if para:
                processed_paragraphs.append(para)
        
        # Join paragraphs with proper spacing
        result = '<br/><br/>'.join(processed_paragraphs)
        
        # Limit length for readability
        if len(result) > 3000:
            result = result[:3000] + "...<br/><br/><i>[Content truncated for PDF display]</i>"
        
        return result
    
    def _format_code_for_pdf(self, code: str) -> str:
        """Format code for PDF display with proper syntax highlighting simulation."""
        if not code:
            return ""
        
        # Clean and format code
        lines = code.split('\n')
        formatted_lines = []
        
        for line in lines:
            # Simple syntax highlighting through formatting
            line = line.replace('import ', '<b>import</b> ')
            line = line.replace('from ', '<b>from</b> ')
            line = line.replace('def ', '<b>def</b> ')
            line = line.replace('class ', '<b>class</b> ')
            line = line.replace('if ', '<b>if</b> ')
            line = line.replace('else:', '<b>else</b>:')
            line = line.replace('for ', '<b>for</b> ')
            line = line.replace('while ', '<b>while</b> ')
            line = line.replace('return ', '<b>return</b> ')
            
            # Escape HTML
            line = line.replace('<', '&lt;').replace('>', '&gt;')
            # Restore our formatting
            line = line.replace('&lt;b&gt;', '<b>').replace('&lt;/b&gt;', '</b>')
            
            formatted_lines.append(line)
        
        return '<br/>'.join(formatted_lines)
