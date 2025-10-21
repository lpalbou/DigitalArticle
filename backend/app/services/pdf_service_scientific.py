"""
Scientific PDF Generation Service with LLM-driven content.

This service creates publication-quality PDF documents with proper scientific
structure, consistent typography, and LLM-generated content sections.
"""

import base64
import io
import logging
from typing import List, Optional, Dict, Any, Tuple

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
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
from .scientific_analysis_service import ScientificAnalysisService

logger = logging.getLogger(__name__)


class SectionBreak(Flowable):
    """Custom flowable for elegant section breaks."""
    
    def __init__(self, width=None, color=None):
        Flowable.__init__(self)
        self.width = width or 15*cm
        self.height = 0.8*cm
        self.color = color or colors.HexColor('#2563eb')
        
    def draw(self):
        self.canv.setStrokeColor(self.color)
        self.canv.setLineWidth(1.5)
        self.canv.line(0, self.height/2, self.width, self.height/2)


class ScientificPDFService:
    """Service for generating publication-quality scientific PDF documents."""
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self.scientific_analysis = ScientificAnalysisService()
        self._setup_consistent_styles()
        
        # Counters for figures and tables
        self.figure_counter = 1
        self.table_counter = 1
        
    def _setup_consistent_styles(self):
        """Set up consistent typography styles for scientific publications."""
        
        # Base font settings for consistency
        base_font = 'Helvetica'
        base_font_bold = 'Helvetica-Bold'
        base_font_italic = 'Helvetica-Oblique'
        
        # Title - Large, bold, centered
        self.styles.add(ParagraphStyle(
            name='ArticleTitle',
            fontName=base_font_bold,
            fontSize=18,
            leading=22,
            spaceAfter=8,
            spaceBefore=0,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#1a202c')
        ))
        
        # Subtitle - Medium, italic, centered
        self.styles.add(ParagraphStyle(
            name='ArticleSubtitle',
            fontName=base_font_italic,
            fontSize=12,
            leading=15,
            spaceAfter=16,
            spaceBefore=4,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#4a5568')
        ))
        
        # Author info - Small, centered
        self.styles.add(ParagraphStyle(
            name='AuthorInfo',
            fontName=base_font,
            fontSize=10,
            leading=12,
            spaceAfter=20,
            spaceBefore=0,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#2d3748')
        ))
        
        # Section headings - Consistent hierarchy
        self.styles.add(ParagraphStyle(
            name='SectionHeading',
            fontName=base_font_bold,
            fontSize=14,
            leading=17,
            spaceBefore=20,
            spaceAfter=10,
            textColor=colors.HexColor('#2b6cb0'),
            alignment=TA_LEFT
        ))
        
        # Subsection headings
        self.styles.add(ParagraphStyle(
            name='SubsectionHeading',
            fontName=base_font_bold,
            fontSize=12,
            leading=15,
            spaceBefore=16,
            spaceAfter=8,
            textColor=colors.HexColor('#2d3748'),
            alignment=TA_LEFT
        ))
        
        # Body text - Consistent throughout
        self.styles.add(ParagraphStyle(
            name='ScientificBody',
            fontName=base_font,
            fontSize=10,
            leading=13,
            spaceBefore=0,
            spaceAfter=10,
            alignment=TA_JUSTIFY,
            textColor=colors.HexColor('#2d3748')
        ))
        
        # Abstract - Highlighted body text
        self.styles.add(ParagraphStyle(
            name='Abstract',
            parent=self.styles['ScientificBody'],
            leftIndent=1*cm,
            rightIndent=1*cm,
            spaceBefore=8,
            spaceAfter=16,
            backColor=colors.HexColor('#f7fafc'),
            borderWidth=0.5,
            borderColor=colors.HexColor('#e2e8f0'),
            borderPadding=12
        ))
        
        # Methodology - Highlighted scientific content
        self.styles.add(ParagraphStyle(
            name='Methodology',
            parent=self.styles['ScientificBody'],
            spaceBefore=8,
            spaceAfter=12,
            backColor=colors.HexColor('#edf2f7'),
            borderWidth=0.5,
            borderColor=colors.HexColor('#4299e1'),
            borderPadding=10
        ))
        
        # Code blocks - Monospace, consistent
        self.styles.add(ParagraphStyle(
            name='CodeBlock',
            fontName='Courier',
            fontSize=8,
            leading=10,
            spaceBefore=8,
            spaceAfter=8,
            leftIndent=0.5*cm,
            rightIndent=0.5*cm,
            backColor=colors.HexColor('#f8f9fa'),
            borderWidth=0.5,
            borderColor=colors.HexColor('#dee2e6'),
            borderPadding=8,
            textColor=colors.HexColor('#2d3748')
        ))
        
        # Captions - Consistent for figures and tables
        self.styles.add(ParagraphStyle(
            name='Caption',
            fontName=base_font,
            fontSize=9,
            leading=11,
            spaceBefore=4,
            spaceAfter=12,
            alignment=TA_JUSTIFY,
            textColor=colors.HexColor('#4a5568')
        ))
        
        # Table headers - Consistent styling
        self.styles.add(ParagraphStyle(
            name='TableHeader',
            fontName=base_font_bold,
            fontSize=9,
            leading=11,
            textColor=colors.HexColor('#2d3748'),
            alignment=TA_CENTER
        ))
        
        # Table cells - Consistent styling
        self.styles.add(ParagraphStyle(
            name='TableCell',
            fontName=base_font,
            fontSize=8,
            leading=10,
            textColor=colors.HexColor('#2d3748'),
            alignment=TA_LEFT
        ))
    
    def generate_pdf(self, notebook: Notebook, include_code: bool = False) -> bytes:
        """
        Generate a publication-quality PDF with LLM-generated scientific content.
        
        Args:
            notebook: The notebook to convert to PDF
            include_code: Whether to include generated code in the PDF
            
        Returns:
            PDF content as bytes
        """
        logger.info(f"Generating scientific PDF for notebook: {notebook.title}")
        
        # Reset counters
        self.figure_counter = 1
        self.table_counter = 1
        
        # Generate comprehensive scientific content using LLM with FULL context
        logger.info("Generating comprehensive scientific content with complete context...")
        scientific_content = self.scientific_analysis.generate_scientific_content(notebook)
        
        # Generate scientific methodology sections for each cell
        logger.info("Generating scientific methodology sections for each cell...")
        methodology_sections = self.scientific_analysis.generate_scientific_methodology_sections(notebook)
        
        # Create PDF buffer
        buffer = io.BytesIO()
        
        # Create document with consistent layout
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=2.5*cm,
            leftMargin=2.5*cm,
            topMargin=2.5*cm,
            bottomMargin=2.5*cm,
            title=notebook.title,
            author=notebook.author
        )
        
        # Build document content
        story = []
        
        # Title page
        self._add_title_page(story, notebook)
        
        # Abstract (use notebook's stored abstract)
        self._add_abstract(story, notebook.abstract)
        
        # Introduction (now with analysis plan)
        self._add_introduction(story, scientific_content.get('introduction', ''))
        
        # Enhanced Methodology with scientific sections
        self._add_enhanced_methodology_section(story, notebook, methodology_sections, include_code)
        
        # Results
        self._add_results_section(story, notebook, scientific_content.get('findings_conclusions', ''))
        
        # Build PDF
        doc.build(story)
        
        # Get PDF bytes
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        logger.info(f"Scientific PDF generated successfully: {len(pdf_bytes)} bytes")
        return pdf_bytes

    def generate_scientific_article_pdf(self, scientific_article: Dict[str, Any], notebook: Notebook, include_code: bool = False) -> bytes:
        """
        Generate a PDF from an LLM-generated scientific article.
        
        Args:
            scientific_article: Complete article structure with LLM-generated content
            notebook: Original notebook for metadata and empirical evidence
            include_code: Whether to include code snippets as empirical evidence
            
        Returns:
            PDF content as bytes
        """
        logger.info(f"Generating PDF from LLM-generated scientific article: {scientific_article.get('title', 'Untitled')}")
        
        # Create PDF buffer
        buffer = io.BytesIO()
        
        # Create document with professional layout
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=2.5*cm,
            leftMargin=2.5*cm,
            topMargin=2.5*cm,
            bottomMargin=2.5*cm,
            title=scientific_article.get('title', notebook.title),
            author=notebook.author
        )
        
        # Build document content
        story = []
        
        # Title page with LLM-generated title
        self._add_article_title_page(story, scientific_article, notebook)
        
        # Abstract (from notebook)
        if scientific_article.get('abstract'):
            self._add_abstract(story, scientific_article['abstract'])
        
        # LLM-generated sections with figures
        sections = scientific_article.get('sections', {})
        section_order = ['introduction', 'methodology', 'results', 'discussion', 'conclusions']
        
        figure_counter = 1
        for section_name in section_order:
            if section_name in sections and sections[section_name]:
                self._add_article_section(story, section_name, sections[section_name])
                
                # Add figures after Results section
                if section_name == 'results':
                    figure_counter = self._add_figures_to_results(story, notebook, figure_counter)
        
        # Empirical evidence (code snippets, data outputs)
        if include_code:
            self._add_empirical_evidence_section(story, notebook)
        
        # Acknowledgments
        self._add_acknowledgments(story, scientific_article.get('metadata', {}))
        
        # Build PDF
        doc.build(story)
        
        # Get PDF bytes
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        logger.info(f"LLM-generated scientific article PDF created successfully: {len(pdf_bytes)} bytes")
        return pdf_bytes

    def _add_article_title_page(self, story: List, scientific_article: Dict[str, Any], notebook: Notebook):
        """Add title page with LLM-generated title."""
        # Use LLM-generated title if available, otherwise notebook title
        title = scientific_article.get('title', notebook.title)
        
        # Title
        title_para = Paragraph(self._clean_text_for_pdf(title), self.styles['Title'])
        story.append(title_para)
        story.append(Spacer(1, 0.5*inch))
        
        # Author and metadata
        author_text = f"<b>Author:</b> {notebook.author}"
        author_para = Paragraph(author_text, self.styles['AuthorInfo'])
        story.append(author_para)
        
        # Generation timestamp
        generated_at = scientific_article.get('metadata', {}).get('generated_at', '')
        if generated_at:
            from datetime import datetime
            try:
                dt = datetime.fromisoformat(generated_at.replace('Z', '+00:00'))
                timestamp_text = f"<b>Generated:</b> {dt.strftime('%B %d, %Y at %H:%M UTC')}"
                timestamp_para = Paragraph(timestamp_text, self.styles['AuthorInfo'])
                story.append(timestamp_para)
            except:
                pass
        
        story.append(Spacer(1, 0.5*inch))
        story.append(PageBreak())

    def _add_article_section(self, story: List, section_name: str, section_content: str):
        """Add a section with LLM-generated content."""
        if not section_content:
            return
        
        # Section heading
        section_title = section_name.replace('_', ' ').title()
        heading = Paragraph(section_title, self.styles['SectionHeading'])
        story.append(heading)
        
        # Section content (LLM-generated)
        content_para = Paragraph(self._clean_text_for_pdf(section_content), self.styles['BodyText'])
        story.append(content_para)
        story.append(Spacer(1, 0.2*inch))

    def _add_empirical_evidence_section(self, story: List, notebook: Notebook):
        """Add empirical evidence section with code snippets and outputs."""
        # Section heading
        heading = Paragraph("Empirical Evidence", self.styles['SectionHeading'])
        story.append(heading)
        
        intro_text = "The following code implementations and outputs provide empirical support for the analysis presented in this article."
        intro_para = Paragraph(intro_text, self.styles['BodyText'])
        story.append(intro_para)
        story.append(Spacer(1, 0.1*inch))
        
        # Add code, results, and figures from each cell
        figure_counter = 1
        for i, cell in enumerate(notebook.cells, 1):
            if cell.code and cell.code.strip():
                # Code snippet
                code_heading = Paragraph(f"Code Snippet {i}", self.styles['SubsectionHeading'])
                story.append(code_heading)
                
                # Clean and format code
                clean_code = self._clean_text_for_pdf(cell.code)
                code_para = Paragraph(f"<font name='Courier' size='8'>{clean_code}</font>", self.styles['CodeBlock'])
                story.append(code_para)
                
                # Output if available
                if cell.last_result and cell.last_result.stdout:
                    output_text = f"<b>Output:</b><br/>{self._clean_text_for_pdf(cell.last_result.stdout)}"
                    output_para = Paragraph(output_text, self.styles['Results'])
                    story.append(output_para)
                
                # Figures if available
                if cell.last_result and cell.last_result.plots:
                    for plot_data in cell.last_result.plots:
                        try:
                            # Add figure
                            self._add_figure_to_story(story, plot_data, f"Figure {figure_counter}", 
                                                    f"Visualization generated from Code Snippet {i}")
                            figure_counter += 1
                        except Exception as e:
                            logger.warning(f"Failed to add figure to PDF: {e}")
                
                story.append(Spacer(1, 0.1*inch))

    def _add_acknowledgments(self, story: List, metadata: Dict[str, Any]):
        """Add acknowledgments section."""
        # Section heading
        heading = Paragraph("Acknowledgments", self.styles['SectionHeading'])
        story.append(heading)
        
        # Acknowledgment text
        ack_text = ("This article was generated using Digital Article, an open-source platform for "
                   "reproducible data analysis and scientific writing. The platform combines computational "
                   "analysis with AI-powered scientific writing to create publication-ready research articles. "
                   "Digital Article is available at: github.com/lpalbou/digitalarticle")
        
        ack_para = Paragraph(ack_text, self.styles['BodyText'])
        story.append(ack_para)
        
        # Timestamp
        generated_at = metadata.get('generated_at', '')
        if generated_at:
            from datetime import datetime
            try:
                dt = datetime.fromisoformat(generated_at.replace('Z', '+00:00'))
                timestamp_text = f"<br/><br/><i>Article generated on {dt.strftime('%B %d, %Y at %H:%M UTC')}</i>"
                timestamp_para = Paragraph(timestamp_text, self.styles['BodyText'])
                story.append(timestamp_para)
            except:
                pass

    def _add_figure_to_story(self, story: List, plot_data: str, figure_title: str, caption: str):
        """Add a figure to the PDF story."""
        try:
            import base64
            from reportlab.platypus import Image
            from reportlab.lib.units import inch
            import io
            from PIL import Image as PILImage
            
            # Decode base64 image data
            image_data = base64.b64decode(plot_data)
            
            # Create PIL image to get dimensions
            pil_image = PILImage.open(io.BytesIO(image_data))
            original_width, original_height = pil_image.size
            
            # Calculate scaled dimensions (max width 6 inches)
            max_width = 6 * inch
            scale_factor = min(max_width / original_width, 1.0)
            scaled_width = original_width * scale_factor
            scaled_height = original_height * scale_factor
            
            # Create ReportLab Image
            img = Image(io.BytesIO(image_data), width=scaled_width, height=scaled_height)
            
            # Add figure title
            figure_heading = Paragraph(figure_title, self.styles['SubsectionHeading'])
            story.append(figure_heading)
            
            # Add the image
            story.append(img)
            
            # Add caption
            if caption:
                caption_para = Paragraph(f"<i>{caption}</i>", self.styles['Caption'])
                story.append(caption_para)
            
            story.append(Spacer(1, 0.2*inch))
            
        except Exception as e:
            logger.error(f"Failed to add figure to PDF: {e}")
            # Add placeholder text instead
            error_para = Paragraph(f"<i>[Figure {figure_title} could not be displayed]</i>", self.styles['BodyText'])
            story.append(error_para)

    def _add_figures_to_results(self, story: List, notebook: Notebook, figure_counter: int) -> int:
        """Add figures inline with the Results section."""
        for i, cell in enumerate(notebook.cells, 1):
            if cell.last_result and cell.last_result.plots:
                for plot_data in cell.last_result.plots:
                    try:
                        # Create descriptive caption based on cell content
                        caption = f"Figure {figure_counter}. "
                        if cell.prompt:
                            # Use first part of prompt as caption
                            prompt_summary = cell.prompt[:100] + "..." if len(cell.prompt) > 100 else cell.prompt
                            caption += f"Visualization of {prompt_summary.lower()}"
                        else:
                            caption += f"Data visualization from analysis step {i}"
                        
                        self._add_figure_to_story(story, plot_data, f"Figure {figure_counter}", caption)
                        figure_counter += 1
                    except Exception as e:
                        logger.warning(f"Failed to add figure {figure_counter} to results: {e}")
        
        return figure_counter
    
    def _add_title_page(self, story: List, notebook: Notebook):
        """Add professional title page."""
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
        Digital Article System<br/>
        Generated on {notebook.updated_at.strftime('%B %d, %Y')}
        """
        author_para = Paragraph(author_info, self.styles['AuthorInfo'])
        story.append(author_para)
        
        # Section break
        story.append(SectionBreak())
        story.append(Spacer(1, 16))
    
    def _add_abstract(self, story: List, abstract_text: str):
        """Add abstract section."""
        if not abstract_text:
            return
            
        # Section heading
        heading = Paragraph("Abstract", self.styles['SectionHeading'])
        story.append(heading)
        
        # Abstract content
        abstract_para = Paragraph(self._clean_text_for_pdf(abstract_text), self.styles['Abstract'])
        story.append(abstract_para)
        
        story.append(Spacer(1, 16))
    
    def _add_introduction(self, story: List, introduction_text: str):
        """Add introduction section."""
        if not introduction_text:
            return
            
        # Section heading
        heading = Paragraph("Introduction", self.styles['SectionHeading'])
        story.append(heading)
        
        # Introduction content
        intro_para = Paragraph(self._clean_text_for_pdf(introduction_text), self.styles['ScientificBody'])
        story.append(intro_para)
        
        story.append(Spacer(1, 16))
    
    def _add_methodology_section(self, story: List, notebook: Notebook, include_code: bool):
        """Add methodology section with scientific explanations."""
        # Section heading
        heading = Paragraph("Methodology", self.styles['SectionHeading'])
        story.append(heading)
        
        methodology_added = False
        
        for i, cell in enumerate(notebook.cells, 1):
            if cell.scientific_explanation:
                methodology_added = True
                
                # Subsection for each methodology
                if cell.prompt:
                    subsection_title = f"{i}. {cell.prompt}"
                    subsection = Paragraph(subsection_title, self.styles['SubsectionHeading'])
                    story.append(subsection)
                
                # Methodology content
                methodology_text = self._clean_text_for_pdf(cell.scientific_explanation)
                methodology_para = Paragraph(methodology_text, self.styles['Methodology'])
                story.append(methodology_para)
                
                # Optional code block
                if include_code and cell.code:
                    code_title = Paragraph("<b>Implementation:</b>", self.styles['ScientificBody'])
                    story.append(code_title)
                    
                    formatted_code = self._format_code_for_pdf(cell.code)
                    code_para = Paragraph(formatted_code, self.styles['CodeBlock'])
                    story.append(code_para)
                
                story.append(Spacer(1, 12))
        
        if not methodology_added:
            # Add general methodology description
            general_method = Paragraph(
                "This analysis employs computational methods and data visualization techniques to examine patterns and relationships within the dataset. Statistical analysis and graphical representation are used to derive insights and support conclusions.",
                self.styles['ScientificBody']
            )
            story.append(general_method)
        
        story.append(Spacer(1, 16))
    
    def _add_enhanced_methodology_section(self, story: List, notebook: Notebook, methodology_sections: List[Dict], include_code: bool):
        """Add enhanced methodology section with LLM-generated scientific content for each cell."""
        heading = Paragraph("2. Methodology", self.styles['SectionHeading'])
        story.append(heading)
        story.append(Spacer(1, 6))

        if methodology_sections:
            for section in methodology_sections:
                # Scientific subsection heading
                sub_heading = Paragraph(f"2.{section['cell_number']} {section['title']}", self.styles['SubsectionHeading'])
                story.append(sub_heading)
                story.append(Spacer(1, 4))

                # LLM-generated scientific methodology content
                methodology_text = self._clean_text_for_pdf(section['content'])
                methodology_para = Paragraph(methodology_text, self.styles['Methodology'])
                story.append(methodology_para)

                # Optional code block for implementation details
                if include_code:
                    # Find the corresponding cell
                    cell = next((c for c in notebook.cells if notebook.cells.index(c) + 1 == section['cell_number']), None)
                    if cell and cell.code:
                        code_title = Paragraph("<b>Implementation Details:</b>", self.styles['ScientificBody'])
                        story.append(code_title)
                        story.append(Spacer(1, 2))

                        formatted_code = self._format_code_for_pdf(cell.code)
                        code_para = Paragraph(formatted_code, self.styles['CodeBlock'])
                        story.append(code_para)

                story.append(Spacer(1, 12))
        else:
            # Fallback to general methodology
            general_method = Paragraph(
                "This analysis employs computational methods and data visualization techniques to examine patterns and relationships within the dataset. Statistical analysis and graphical representation are used to derive insights and support conclusions.",
                self.styles['ScientificBody']
            )
            story.append(general_method)

        story.append(Spacer(1, 16))
    
    def _add_results_section(self, story: List, notebook: Notebook, findings_text: str):
        """Add results section with proper figure and table numbering."""
        # Section heading
        heading = Paragraph("Results", self.styles['SectionHeading'])
        story.append(heading)
        
        # Add findings and conclusions first
        if findings_text:
            findings_para = Paragraph(self._clean_text_for_pdf(findings_text), self.styles['ScientificBody'])
            story.append(findings_para)
            story.append(Spacer(1, 12))
        
        # Add results from each cell
        for i, cell in enumerate(notebook.cells, 1):
            if cell.last_result and (cell.last_result.plots or cell.last_result.tables or 
                                   cell.last_result.interactive_plots or cell.last_result.stdout):
                
                # Subsection heading
                if cell.prompt:
                    subsection_title = f"{i}. {cell.prompt}"
                    subsection = Paragraph(subsection_title, self.styles['SubsectionHeading'])
                    story.append(subsection)
                
                # Add text output if meaningful
                if cell.last_result.stdout:
                    output_text = self._clean_text_for_pdf(cell.last_result.stdout)
                    if len(output_text.strip()) > 10:  # Only add if substantial
                        output_para = Paragraph(output_text, self.styles['ScientificBody'])
                        story.append(output_para)
                        story.append(Spacer(1, 8))
                
                # Add figures (plots)
                if cell.last_result.plots:
                    for plot_b64 in cell.last_result.plots:
                        self._add_figure(story, plot_b64, cell.prompt or f"Analysis {i}")
                
                # Add interactive plots
                if cell.last_result.interactive_plots:
                    for plot_data in cell.last_result.interactive_plots:
                        self._add_interactive_plot_description(story, plot_data)
                
                # Add tables
                if cell.last_result.tables:
                    for table_data in cell.last_result.tables:
                        self._add_professional_table(story, table_data)
                
                story.append(Spacer(1, 16))
    
    def _add_figure(self, story: List, plot_b64: str, context: str = ""):
        """Add a professionally formatted figure with proper numbering."""
        try:
            # Decode and process image
            image_data = base64.b64decode(plot_b64)
            image_buffer = io.BytesIO(image_data)
            
            # Create PIL image to get dimensions
            pil_img = PILImage.open(image_buffer)
            img_width, img_height = pil_img.size
            
            # Calculate scaled dimensions for optimal layout
            max_width = 12*cm  # Consistent figure width
            max_height = 10*cm
            
            # Maintain aspect ratio
            scale_factor = min(max_width / img_width, max_height / img_height)
            scaled_width = img_width * scale_factor
            scaled_height = img_height * scale_factor
            
            # Reset buffer position
            image_buffer.seek(0)
            
            # Create ReportLab image
            img = Image(image_buffer, width=scaled_width, height=scaled_height)
            img.hAlign = 'CENTER'
            story.append(img)
            
            # Add professional caption
            caption_text = f"<b>Figure {self.figure_counter}.</b> {context}"
            if not context.endswith('.'):
                caption_text += "."
            
            caption = Paragraph(caption_text, self.styles['Caption'])
            story.append(caption)
            story.append(Spacer(1, 12))
            
            self.figure_counter += 1
            
        except Exception as e:
            logger.warning(f"Failed to add figure {self.figure_counter}: {e}")
            # Add error placeholder
            error_text = Paragraph(
                f"<b>Figure {self.figure_counter}.</b> [Visualization not available]",
                self.styles['Caption']
            )
            story.append(error_text)
            self.figure_counter += 1
    
    def _add_interactive_plot_description(self, story: List, plot_data: Dict):
        """Add description for interactive plots."""
        plot_name = plot_data.get('name', f'Interactive Analysis {self.figure_counter}')
        
        description = Paragraph(
            f"<b>Figure {self.figure_counter}.</b> Interactive visualization: {plot_name}. "
            "This analysis includes interactive elements available in the digital version.",
            self.styles['Caption']
        )
        story.append(description)
        story.append(Spacer(1, 12))
        self.figure_counter += 1
    
    def _add_professional_table(self, story: List, table_data: Dict):
        """Add a professionally formatted table with proper numbering."""
        try:
            table_name = table_data.get('name', f'Data Table {self.table_counter}')
            columns = table_data.get('columns', [])
            data = table_data.get('data', [])
            shape = table_data.get('shape', [0, 0])
            
            if not data or not columns:
                return
            
            # Table caption
            caption_text = f"<b>Table {self.table_counter}.</b> {table_name}"
            if shape[0] > 0:
                caption_text += f" (n = {shape[0]} observations)"
            caption_text += "."
            
            caption = Paragraph(caption_text, self.styles['Caption'])
            story.append(caption)
            story.append(Spacer(1, 6))
            
            # Prepare table data (limit rows for readability)
            max_rows = 12
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
                        if len(value) > 25:
                            value = value[:22] + "..."
                        table_row.append(Paragraph(value, self.styles['TableCell']))
                    table_rows.append(table_row)
                else:
                    table_row = [Paragraph(str(val)[:25], self.styles['TableCell']) for val in row[:len(columns)]]
                    table_rows.append(table_row)
            
            # Create table with professional styling
            pdf_table = Table(table_rows, repeatRows=1)
            
            # Consistent table styling
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
            self.table_counter += 1
            
        except Exception as e:
            logger.warning(f"Failed to add table {self.table_counter}: {e}")
            error_text = Paragraph(
                f"<b>Table {self.table_counter}.</b> [Table data not available]",
                self.styles['Caption']
            )
            story.append(error_text)
            self.table_counter += 1
    
    def _clean_text_for_pdf(self, text: str) -> str:
        """Clean and format text for optimal PDF display."""
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
        if len(result) > 4000:
            result = result[:4000] + "...<br/><br/><i>[Content truncated for PDF display]</i>"
        
        return result
    
    def _format_code_for_pdf(self, code: str) -> str:
        """Format code for PDF display with basic syntax highlighting."""
        if not code:
            return ""
        
        # Clean and format code
        lines = code.split('\n')
        formatted_lines = []
        
        for line in lines:
            # Basic syntax highlighting
            line = line.replace('import ', '<b>import</b> ')
            line = line.replace('from ', '<b>from</b> ')
            line = line.replace('def ', '<b>def</b> ')
            line = line.replace('class ', '<b>class</b> ')
            line = line.replace('if ', '<b>if</b> ')
            line = line.replace('else:', '<b>else</b>:')
            line = line.replace('for ', '<b>for</b> ')
            line = line.replace('return ', '<b>return</b> ')
            
            # Escape HTML but preserve our formatting
            line = line.replace('<', '&lt;').replace('>', '&gt;')
            line = line.replace('&lt;b&gt;', '<b>').replace('&lt;/b&gt;', '</b>')
            
            formatted_lines.append(line)
        
        return '<br/>'.join(formatted_lines)
