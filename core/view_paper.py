#Tiny function to view a Word doc for randomized papers

from django.shortcuts import get_object_or_404, render
from django.conf import settings
from .models import Assessment

def view_randomized_paper(request, assessment_id):
    assessment = get_object_or_404(Assessment, id=assessment_id, paper_type='randomized')
    # Assume assessment.file is the Word doc stored in MEDIA
    file_url = assessment.file.url if assessment.file else None
    return render(request, 'core/view_randomized_paper.html', {'file_url': file_url, 'assessment': assessment})