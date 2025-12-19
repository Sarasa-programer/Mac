import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging
import os

logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER", "")
        self.smtp_password = os.getenv("SMTP_PASSWORD", "")
        self.enabled = bool(self.smtp_user and self.smtp_password)

    def send_search_results(self, to_email: str, query: str, results: list):
        """
        Sends search results or no-results notification via email.
        """
        if not self.enabled:
            logger.info("Email service disabled (missing credentials). Skipping email.")
            return False

        try:
            msg = MIMEMultipart()
            msg['From'] = self.smtp_user
            msg['To'] = to_email
            
            if results:
                subject = f"PubMed Search Results: {query}"
                body = f"<h2>Search Results for '{query}'</h2><ul>"
                for article in results:
                    title = article.get('title', 'No Title')
                    url = article.get('url', '#')
                    body += f"<li><a href='{url}'>{title}</a></li>"
                body += "</ul>"
            else:
                subject = f"PubMed Search: No Results for '{query}'"
                body = f"""
                <h2>No Results Found</h2>
                <p>We could not find any articles matching your query:</p>
                <blockquote><strong>{query}</strong></blockquote>
                <p>Try adjusting your search terms or checking for typos.</p>
                """

            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'html'))

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
            
            logger.info(f"Email sent to {to_email}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False
