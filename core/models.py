from django.db import models
from django.contrib.auth.models import AbstractUser, UserManager
from django.utils.timezone import now
from django.core.exceptions import ValidationError
from django.conf import settings
import random
from django.utils.html import mark_safe
import base64 
import uuid

#************************
# Qualification creation
#************************
from django.db import models
from django.core.exceptions import ValidationError

class Qualification(models.Model):
    name = models.CharField(max_length=100, unique=True)
    saqa_id = models.CharField(max_length=20, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @classmethod
    def get_module_choices_for_type(cls, qual_type):
        from . import qualification_registry

        modules = qualification_registry.get_module_choices(qual_type)
        if not modules:
            return []
        return [
            (m.get('code'), m.get('label') or m.get('code'))
            for m in modules
            if m.get('code')
        ]

    def clean(self):
        from . import qualification_registry

        entry = qualification_registry.find_entry(self.name)
        expected_saqa = entry.get('saqa_id') if entry else None
        if expected_saqa and self.saqa_id != expected_saqa:
            raise ValidationError(f"SAQA ID for {self.name} must be {expected_saqa}")

    def __str__(self):
        return f"{self.name} (SAQA: {self.saqa_id})"


#****************
# Custom User
#****************
class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ('default',         'Awaiting Activation'),
        ('admin',           'Administrator'),
        ('assessor_dev',    'Assessor (Developer)'),
        ('moderator',       'Moderator (Developer)'),
        ('qcto',            'QCTO Validator'),
        ('etqa',            'ETQA'),
        ('learner',         'Learner'),
        ('assessor_marker', 'Assessor (Marker)'),
        ('internal_mod',    'Internal Moderator'),
        ('external_mod',    'External Moderator (QALA)'),
        ('assessment_center', 'Assessment Center')
    ]

    role                     = models.CharField(max_length=30, choices=ROLE_CHOICES, default='admin')
    qualification            = models.ForeignKey(
                                  Qualification,
                                  on_delete=models.SET_NULL,
                                  null=True, blank=True,
                                  related_name='users'
                              )
    email                    = models.EmailField(unique=True)
        ###########################################
    student_number = models.CharField(
        max_length=50, 
        unique=True, 
        null=True, 
        blank=True,
        help_text="Unique student number for learners"
    )
    ############################################

    ####################################################
    assessment_centre = models.ForeignKey(
        'AssessmentCentre',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assessment_users'
    )
    ####################################################
    objects                  = UserManager()
    created_at               = models.DateTimeField(auto_now_add=True)
    activated_at             = models.DateTimeField(default=now)
    deactivated_at           = models.DateTimeField(null=True, blank=True)
    qualification_updated_at = models.DateTimeField(null=True, blank=True)
    last_updated_at          = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    @property
    def name(self):
        full = f"{self.first_name} {self.last_name}".strip()
        return full or self.username 
    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.get_role_display()})"

    def save(self, *args, **kwargs):
        if self.role == 'assessment_center' and self.assessment_centre:
            self.qualification = self.assessment_centre.qualification_assigned

        if self.pk:
            original = CustomUser.objects.get(pk=self.pk)
            if original.qualification != self.qualification:
                self.qualification_updated_at = now()
        else:
            self.qualification_updated_at = now()  # First-time save

        super().save(*args, **kwargs)


    class Meta:
        ordering = ['-created_at']


    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.get_role_display()})"

#************************
# Question bank entry
#************************
class QuestionBankEntry(models.Model):
    QUESTION_TYPE_CHOICES = [
        ("standard",   "Standard"),
        ("case_study", "Case Study"),
        ("mcq",        "Multiple Choice"),
    ]

    qualification  = models.ForeignKey(Qualification, on_delete=models.SET_NULL, null=True)
    question_type  = models.CharField(max_length=20, choices=QUESTION_TYPE_CHOICES, default="standard")
    text           = models.TextField()
    marks          = models.PositiveIntegerField()
    case_study     = models.ForeignKey("CaseStudy", on_delete=models.SET_NULL, null=True, blank=True)
    created_at     = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.get_question_type_display()}] {self.text[:30]}…"


#****************
# MCQ options
#****************
# class MCQOption(models.Model):
#     question = models.ForeignKey(
#         QuestionBankEntry,
#         on_delete=models.CASCADE,
#         limit_choices_to={"question_type": "mcq"},
#         related_name="options"
#     )
#     text = models.CharField(max_length=255)
#     is_correct = models.BooleanField(default=False)

#     def __str__(self):
#         return f"{'✔' if self.is_correct else '✗'} {self.text}"


#*****************************************
# Assessment + Build-A-Paper & Randomization
#*****************************************
class Assessment(models.Model):
    PAPER_TYPE_CHOICES = [
        ('admin_upload', 'Admin Upload'),
        ('randomized', 'Randomized Paper')
    ]
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending_moderation', 'Pending Moderation'),
        ('moderated', 'Moderated'),
        ('pending_etqa', 'Pending ETQA Review'),
        ('etqa_approved', 'ETQA Approved'),
        ('etqa_rejected', 'ETQA Rejected'),
        ('pending_qcto', 'Pending QCTO Review'),
        ('qcto_approved', 'QCTO Approved'),
        ('qcto_rejected', 'QCTO Rejected'),
        ("Released to students", "Released to students"),
        ('active', 'Active'),
        ('archived', 'Archived')
    ]

    eisa_id = models.CharField(max_length=50)
    qualification = models.ForeignKey(Qualification, on_delete=models.SET_NULL, null=True)
    paper = models.CharField(max_length=50)
    paper_type = models.CharField(
        max_length=50,
        choices=PAPER_TYPE_CHOICES,
        default='admin_upload'
    )
    paper_link = models.ForeignKey(
        "Paper",
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="assessments"
    )
    extractor_paper = models.OneToOneField(
        'ExtractorPaper',
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='assessment_record'
    )
    saqa_id = models.CharField(max_length=50, blank=True, null=True)
    moderator = models.CharField(max_length=100, blank=True)
    file = models.FileField(upload_to="assessments/", blank=True, null=True)
    
    # Memo field for admin uploads
    memo = models.FileField(
        upload_to="assessments/memos/", 
        blank=True, 
        null=True,
        help_text="Memo file for admin-uploaded assessments"
    )
    
    comment = models.TextField(blank=True)
    forward_to_moderator = models.BooleanField(default=False)
    moderator_report = models.FileField(
        upload_to="moderator_reports/", 
        blank=True, 
        null=True,
        help_text="Word document report from moderator"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    qcto_report = models.FileField(
        upload_to="qcto_reports/", 
        blank=True, 
        null=True,
        help_text="Word document report from qcto"
    )
    
    # ETQA fields - only used for randomized papers
    is_selected_by_etqa = models.BooleanField(default=False)
    memo_file = models.FileField(
        upload_to='memos/randomized/', 
        null=True, 
        blank=True,
        help_text="Memo file for randomized assessments requiring ETQA approval"
    )
    etqa_approved = models.BooleanField(default=False)
    etqa_comments = models.TextField(blank=True)
    etqa_approved_date = models.DateTimeField(null=True, blank=True)

    # Add status tracking fields
    status = models.CharField(
        max_length=50,
        choices=STATUS_CHOICES,
        default='draft'
    )
    status_changed_at = models.DateTimeField(auto_now_add=True)
    status_changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='status_changes'
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="assessments_created"
    )
    module_name = models.CharField(
        max_length=100,
        help_text="e.g. Chemical Operations",
        default="Unknown Module"
    )
    module_number = models.CharField(
        max_length=2,
        help_text="Module identifier (1A, 1B, etc)",
        default="1A"
    )

    def get_memo_path(self, filename):
        """Generate organized path for memo files"""
        safe_name = self.module_name.replace(' ', '_')
        return f'assessments/memos/{safe_name}/{self.module_number}/{filename}'

    def requires_etqa_approval(self):
        """Only randomized papers require ETQA approval"""
        return self.paper_type == 'randomized'

    def clean(self):
        """Validation to ensure correct memo field usage"""
        if self.paper_type == 'admin_upload':
            # Admin uploads should use the 'memo' field
            if self.memo_file:
                raise ValidationError({
                    'memo_file': 'For admin uploads, use the standard memo field'
                })
        else:
            # Randomized papers should use memo_file
            if self.memo:
                raise ValidationError({
                    'memo': 'For randomized papers, use the memo_file field'
                })

    def save(self, *args, **kwargs):
        self.clean()
        # Remove the PDF renaming logic - let files keep their original names
        super().save(*args, **kwargs)

    # — new M2M through-model fields —
    questions = models.ManyToManyField(
        'QuestionBankEntry',
        through='AssessmentQuestion',
        related_name='assessments'
    )
    questions_randomized = models.BooleanField(default=False)

    def randomize_questions(self):
        linked_qs = list(self.questions.all())
        if not linked_qs:
            return
        random.shuffle(linked_qs)
        for idx, q in enumerate(linked_qs, start=1):
            aq, _ = AssessmentQuestion.objects.get_or_create(
                assessment=self,
                question=q,
                defaults={'order': idx}
            )
            aq.order = idx
            aq.save(update_fields=['order'])
        self.questions_randomized = True
        self.save(update_fields=['questions_randomized'])

    def update_status(self, new_status, user):
        """Update assessment status with audit trail"""
        if new_status in dict(self.STATUS_CHOICES):
            self.status = new_status
            self.status_changed_at = now()
            self.status_changed_by = user
            self.save()

    def get_next_status(self):
        """Determine next status based on paper type and current status"""
        if self.paper_type == 'admin_upload':
            STATUS_FLOW = {
                'draft': 'pending_moderation',
                'pending_moderation': 'moderated',
                'moderated': 'pending_qcto',
                'pending_qcto': 'active'
            }
        else:  # randomized paper
            STATUS_FLOW = {
                'draft': 'pending_etqa',
                'pending_etqa': 'etqa_approved',
                'etqa_approved': 'pending_moderation',
                'pending_moderation': 'moderated',
                'moderated': 'pending_qcto',
                'pending_qcto': 'active'
            }
        return STATUS_FLOW.get(self.status)

    def can_transition_to(self, new_status, user):
        """Check if status transition is allowed for user role"""
        ALLOWED_TRANSITIONS = {
            'moderator': ['moderated', 'pending_moderation'],
            'etqa': ['etqa_approved', 'etqa_rejected'],
            'qcto': ['qcto_approved', 'qcto_rejected'],
            'admin': [s[0] for s in self.STATUS_CHOICES]
        }
        return new_status in ALLOWED_TRANSITIONS.get(user.role, [])

    class Meta:
        permissions = [
            ("can_moderate", "Can moderate assessments"),
            ("can_etqa_review", "Can review as ETQA"),
            ("can_qcto_review", "Can review as QCTO")
        ]

    def __str__(self):
        return f"{self.paper} - {self.qualification}"
class AssessmentQuestion(models.Model):
    """Through-model to store per-question content, marks, and order."""
    assessment   = models.ForeignKey(Assessment, on_delete=models.CASCADE)
    question     = models.ForeignKey(QuestionBankEntry, on_delete=models.CASCADE)
    order        = models.PositiveIntegerField(default=0)
    marks        = models.PositiveIntegerField(default=0)
    content_html = models.TextField(
        blank=True,
        help_text="Paste question text, tables, images (HTML) here."
    )

    class Meta:
        unique_together = ('assessment', 'question')
        ordering = ['order']

    def rendered_content(self):
        return mark_safe(self.content_html)

class CaseStudy(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()

    def __str__(self):
        return self.title

class GeneratedQuestion(models.Model):
    assessment = models.ForeignKey(
        Assessment,
        related_name='generated_questions',
        on_delete=models.CASCADE
    )
    text = models.TextField()
    marks = models.PositiveIntegerField()
    case_study = models.ForeignKey(
        CaseStudy,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.text[:50]}… ({self.marks} marks)"



class MCQOption(models.Model):
    question = models.ForeignKey(
        QuestionBankEntry,
        on_delete=models.CASCADE,
        limit_choices_to={"question_type": "mcq"},
        related_name="options"
    )
    text = models.CharField(max_length=255)
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return f"{'✔' if self.is_correct else '✗'} {self.text}"

class ChecklistItem(models.Model):
    label = models.CharField(max_length=200)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.label



class AssessmentCentre(models.Model):
    name = models.CharField(max_length=200)
    location = models.CharField(max_length=255, blank=True)
    qualification_assigned = models.ForeignKey(Qualification, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return self.name

# Batch model ___________________________________________________________________________________________#

class Batch(models.Model):
    center = models.ForeignKey('AssessmentCentre', on_delete=models.CASCADE)
    qualification = models.ForeignKey('Qualification', on_delete=models.CASCADE)
    assessment = models.ForeignKey('Assessment', on_delete=models.CASCADE)
    assessment_date = models.DateField()
    # number_of_learners = models.PositiveIntegerField()
    submitted_to_center = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Batch - {self.center.name} | {self.qualification.name} | {self.assessment.eisa_id}"

#students model -------------------------------------------------------------------
class ExamAnswer(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    question = models.ForeignKey('GeneratedQuestion', on_delete=models.CASCADE)
    answer_text = models.TextField()
    submitted_at = models.DateTimeField(auto_now_add=True)
    attempt_number = models.PositiveSmallIntegerField(default=1)  # Track attempts

    class Meta:
        unique_together = ('user', 'question', 'attempt_number')  # Include attempts 
        verbose_name = 'Exam Answer'
        verbose_name_plural = 'Exam Answers'

    @property
    def assessment(self):
        """Quick access to the assessment through the question"""
        return self.question.assessment

    def __str__(self):
        return f"Answer by {self.user} for {self.question} (Attempt {self.attempt_number})"

# <-------------------------------------------Questions storage Models --------------------------------------------------->
# core/models.py
from django.db import models


class Paper(models.Model):
    name = models.CharField(max_length=255)
    qualification = models.ForeignKey(Qualification, on_delete=models.CASCADE)
    is_randomized = models.BooleanField(default=False)
    structure_json = models.JSONField(default=dict, blank=True)
    total_marks = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="papers_created"
    )

    def __str__(self):
        return f"{self.name} ({self.qualification})"



class PaperBankEntry(models.Model):
    assessment = models.OneToOneField('Assessment', on_delete=models.CASCADE, related_name='paper_bank_entry')
    original_file = models.FileField(upload_to='paper_bank/')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Paper bank entry for {self.assessment.eisa_id}"





class ExamNode(models.Model):
    """Model for storing question/content nodes of a paper"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    paper = models.ForeignKey(Paper, on_delete=models.CASCADE, related_name='nodes')
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='children')
    node_type = models.CharField(max_length=20, choices=[
        ('question', 'Question'),
        ('table', 'Table'),
        ('image', 'Image'),
        ('text', 'Text'),
        ('instruction', 'Instruction'),
    ])
    number = models.CharField(max_length=20, blank=True, null=True)
    text = models.TextField(blank=True, null=True)
    marks = models.CharField(max_length=10, blank=True, null=True)
    content = models.JSONField(default=list, blank=True)
    order_index = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order_index']
        indexes = [
            models.Index(fields=['paper', 'node_type']),
            models.Index(fields=['paper', 'number']),
        ]
        
    def __str__(self):
        return f"{self.node_type}: {self.number or 'No number'} ({self.id})"
        
    def clean_content(self):
        """Ensure content is a list"""
        if self.content is None:
            self.content = []
        return self.content

class Feedback(models.Model):
    assessment = models.ForeignKey(
        Assessment,
        on_delete=models.CASCADE,
        related_name='feedbacks'
    )
    to_user = models.CharField(max_length=100)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    STATUS_CHOICES = [
        ("Pending", "Pending"),
        ("Revised", "Revised"),
        ("Completed", "Completed"),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="Pending")

    def __str__(self):
        return f"{self.assessment.eisa_id} → {self.to_user}"


class RegexPattern(models.Model):
    pattern = models.TextField()
    description = models.TextField()
    match_score = models.FloatField()
    example_usage = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

##############new model for storing exam submissions ##############
# models.py - Add grading fields to ExamSubmission
class ExamSubmission(models.Model):
    # Student info
    student = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True)  
    offline_student = models.ForeignKey('OfflineStudent', on_delete=models.CASCADE, null=True, blank=True)  
    student_number = models.CharField(max_length=50)
    student_name = models.CharField(max_length=100)

    # Paper info
    paper = models.ForeignKey(Paper, on_delete=models.SET_NULL, null=True, blank=True)
    assessment = models.ForeignKey(Assessment, on_delete=models.SET_NULL, null=True, blank=True)
    attempt_number = models.IntegerField()
    pdf_file = models.FileField(upload_to='exam_submissions/%Y/%m/%d/')
    submitted_at = models.DateTimeField(auto_now_add=True)
    is_offline = models.BooleanField(default=False)

    # Marker grading
    marks = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    total_marks = models.DecimalField(max_digits=5, decimal_places=2, default=100.00)
    graded_by = models.ForeignKey(
        CustomUser,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="graded_submissions"
    )
    graded_at = models.DateTimeField(null=True, blank=True)
    feedback = models.TextField(blank=True)
    marked_paper = models.FileField(upload_to='marked_papers/marker/%Y/%m/%d/', null=True, blank=True)  # NEW FIELD

    # Internal Moderator grading
    internal_marks = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    internal_total_marks = models.DecimalField(max_digits=5, decimal_places=2, default=100.00)
    internal_graded_by = models.ForeignKey(
        CustomUser,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="internal_graded_submissions"
    )
    internal_graded_at = models.DateTimeField(null=True, blank=True)
    internal_feedback = models.TextField(blank=True)
    internal_marked_paper = models.FileField(upload_to='marked_papers/internal/%Y/%m/%d/', null=True, blank=True)  # NEW FIELD

    # External Moderator grading
    external_marks = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    external_total_marks = models.DecimalField(max_digits=5, decimal_places=2, default=100.00)
    external_graded_by = models.ForeignKey(
        CustomUser,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="external_graded_submissions"
    )
    external_graded_at = models.DateTimeField(null=True, blank=True)
    external_feedback = models.TextField(blank=True)
    external_marked_paper = models.FileField(upload_to='marked_papers/external/%Y/%m/%d/', null=True, blank=True)  # NEW FIELD

    class Meta:
        ordering = ['-submitted_at']

    def __str__(self):
        return f"{self.student_number} - {self.paper.name if self.paper else 'No Paper'} - Attempt {self.attempt_number}"

    def save(self, *args, **kwargs):
        # Auto-set is_offline and student details
        if self.offline_student:
            self.is_offline = True
            self.student_number = self.offline_student.student_number
            self.student_name = f"{self.offline_student.first_name} {self.offline_student.last_name}"
        elif self.student:
            self.student_number = self.student.student_number
            self.student_name = f"{self.student.first_name} {self.student.last_name}"
        super().save(*args, **kwargs)

    @property
    def status(self):
        """Return submission status based on grading progress"""
        if self.external_marks is not None:
            return "Finalized"
        elif self.internal_marks is not None:
            return "Reviewed"
        elif self.marks is not None:
            return "Graded by Marker"
        return "Pending"
class OfflineStudent(models.Model):
    STUDENT_STATUS = [
        ('present', 'Present'),
        ('absent', 'Absent'),
    ]
    
    student_number = models.CharField(max_length=20, unique=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(blank=True)
    qualification = models.ForeignKey(Qualification, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=10, choices=STUDENT_STATUS, default='present')
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        related_name="offline_students_created"
    )
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.student_number} - {self.first_name} {self.last_name}"  
    
# Extractor models integrated from Chieta_Paper_Extractor
class ExtractorPaper(models.Model):
    title = models.CharField(max_length=255, blank=True)
    original_file = models.FileField(upload_to="uploads/")
    created_at = models.DateTimeField(auto_now_add=True)
    # Per-paper system prompt for AI classification/grouping
    system_prompt = models.TextField(blank=True, default="")
    # Optional identifiers for tracking and reconstruction
    module_name = models.CharField(max_length=255, blank=True, default="")
    paper_number = models.CharField(max_length=50, blank=True, default="")
    paper_letter = models.CharField(max_length=10, blank=True, default="")

    def __str__(self):
        return f"{self.title or 'Untitled Paper'} ({self.module_name or 'No Module'})"


class ExtractorBlock(models.Model):
    PAPER_BLOCK_TYPES = [
        ("paragraph", "Paragraph"),
        ("table", "Table"),
        ("image", "Image"),
        ("heading", "Heading"),
        ("instruction", "Instruction"),
        ("rubric", "Rubric"),
    ]
    paper = models.ForeignKey(ExtractorPaper, on_delete=models.CASCADE, related_name="blocks")
    order_index = models.IntegerField()
    block_type = models.CharField(max_length=20, choices=PAPER_BLOCK_TYPES)
    # Raw XML for audit/debug, plus a normalized text for rendering/search
    xml = models.TextField(blank=True)
    text = models.TextField(blank=True)
    # Optional: absolute positioning (if you compute it later)
    x = models.FloatField(null=True, blank=True)
    y = models.FloatField(null=True, blank=True)
    w = models.FloatField(null=True, blank=True)
    h = models.FloatField(null=True, blank=True)
    # Auto-detected question segmentation
    is_qheader = models.BooleanField(default=False)
    detected_qnum = models.CharField(max_length=50, blank=True)
    detected_marks = models.CharField(max_length=50, blank=True)
    # Optional randomized ordering (per-paper variant)
    rand_order_index = models.IntegerField(null=True, blank=True)

    class Meta:
        ordering = ['order_index']


class ExtractorBlockImage(models.Model):
    block = models.ForeignKey(ExtractorBlock, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="paper_images/")


class ExtractorUserBox(models.Model):
    """Stores user-drawn boxes & metadata over the rendered page."""
    paper = models.ForeignKey(ExtractorPaper, on_delete=models.CASCADE, related_name="user_boxes")
    # bounding box in container coordinates (CSS pixels) for simplicity
    x = models.FloatField()
    y = models.FloatField()
    w = models.FloatField()
    h = models.FloatField()
    # Save order for reconstruction
    order_index = models.IntegerField(default=0)
    question_number = models.CharField(max_length=50, blank=True)
    marks = models.CharField(max_length=50, blank=True)
    qtype = models.CharField(max_length=50, blank=True)
    parent_number = models.CharField(max_length=50, blank=True)
    header_label = models.CharField(max_length=255, blank=True)
    case_study_label = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    # Captured content from selection (JSON string)
    content_type = models.CharField(max_length=50, blank=True)
    content = models.TextField(blank=True)

    def display_qtype(self):
        mapping = {
            "question": "Question",
            "question_part": "Question Part",
            "question_header": "Question Header",
            "case_study": "Case Study",
            "rubric": "Rubric",
            "instruction": "Instruction",
            "cover_page": "Cover Page",
            "heading": "Heading",
        }
        return mapping.get(self.qtype, self.qtype or "(type)")

    class Meta:
        ordering = ['order_index']


class ExtractorTestPaper(models.Model):
    """Stores a randomized test assembled from the bank of boxes."""
    title = models.CharField(max_length=255, blank=True, default="")
    module_name = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title or 'Untitled Test'} ({self.module_name or 'No Module'})"


class ExtractorTestItem(models.Model):
    test = models.ForeignKey(ExtractorTestPaper, on_delete=models.CASCADE, related_name="items")
    order_index = models.IntegerField(default=0)
    question_number = models.CharField(max_length=50, blank=True)
    marks = models.CharField(max_length=50, blank=True)
    qtype = models.CharField(max_length=50, blank=True)
    content_type = models.CharField(max_length=50, blank=True)
    content = models.TextField(blank=True)  # JSON string copied from UserBox

    class Meta:
        ordering = ['order_index']


