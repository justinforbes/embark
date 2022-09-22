import logging

from django import forms

from tracker import models

logger = logging.getLogger(__name__)

class DateInput(forms.DateInput):
    input_type = 'date'

class TimeForm(forms.Form):

    date = forms.DateField(widget = DateInput())