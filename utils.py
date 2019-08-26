import io
import os
import re
import nltk
import spacy
import pandas as pd
import docx2txt
import subprocess
from datetime import datetime
from dateutil import relativedelta
import constants as cs
from spacy.matcher import Matcher
from pdfminer.converter import TextConverter
from pdfminer.pdfinterp import PDFPageInterpreter
from pdfminer.pdfinterp import PDFResourceManager
from pdfminer.layout import LAParams
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfparser import PDFSyntaxError
from nltk.stem import WordNetLemmatizer
from nltk.corpus import stopwords
import spacy
from fuzzywuzzy import fuzz 
from fuzzywuzzy import process
from tabula import read_pdf
from dateutil.parser import parse
import datetime
import dateutil.parser as parser
import subprocess


def hasNumbers(inputString):
    return any(char.isdigit() for char in inputString)


def is_date(string, fuzzy=False):
    """
    Return whether the string can be interpreted as a date.

    :param string: str, string to check for date
    :param fuzzy: bool, ignore unknown tokens in string if True
    """
    try: 
        parse(string, fuzzy=fuzzy)
        return True

    except ValueError:
        return False
    except:
        return False

cv_tokens_list_nlp=[]
name_tokens=[]
cv_entity_list=[]
cv_noun_list=[]
name_tokens_list=[]
marital_status_list=['single','married','divorced','separated','widowed','unmarried']
fist_name=' '
middle_name='NA'
last_name=' '
final_name=' '

nlp=spacy.load('en_core_web_sm')

# Reads Indian Names from the file, reduce all to lower case for easy comparision [Name lists]
indianNames = open("allNames.txt", "r").read().lower()
# Lookup in a set is much faster
indianNames = set(indianNames.split())


if os.name != 'nt':
    import textract

def extract_text_from_pdf(pdf_path):
    '''
    Helper function to extract the plain text from .pdf files

    :param pdf_path: path to PDF file to be extracted (remote or local)
    :return: iterator of string of extracted text
    '''
    # https://www.blog.pythonlibrary.org/2018/05/03/exporting-data-from-pdfs-with-python/
    if not isinstance(pdf_path, io.BytesIO):
        # extract text from local pdf file
        with open(pdf_path, 'rb') as fh:
            try:
                for page in PDFPage.get_pages(fh, 
                                            caching=True,
                                            check_extractable=True):
                    resource_manager = PDFResourceManager()
                    fake_file_handle = io.StringIO()
                    converter = TextConverter(resource_manager, fake_file_handle, codec='utf-8', laparams=LAParams())
                    page_interpreter = PDFPageInterpreter(resource_manager, converter)
                    page_interpreter.process_page(page)
        
                    text = fake_file_handle.getvalue()
                    yield text
        
                    # close open handles
                    converter.close()
                    fake_file_handle.close()
            except PDFSyntaxError:
                return
    else:
        # extract text from remote pdf file
        try:
            for page in PDFPage.get_pages(pdf_path, 
                                            caching=True,
                                            check_extractable=True):
                resource_manager = PDFResourceManager()
                fake_file_handle = io.StringIO()
                converter = TextConverter(resource_manager, fake_file_handle, codec='utf-8', laparams=LAParams())
                page_interpreter = PDFPageInterpreter(resource_manager, converter)
                page_interpreter.process_page(page)
    
                text = fake_file_handle.getvalue()
                yield text
    
                # close open handles
                converter.close()
                fake_file_handle.close()
        except PDFSyntaxError:
            return


def get_number_of_pages(file_name):
    try:
        if isinstance(file_name, io.BytesIO):
            # for remote pdf file
            count = 0
            for page in PDFPage.get_pages(file_name, 
                                        caching=True,
                                        check_extractable=True):
                    count += 1
            return count
        else:
            # for local pdf file
            if file_name.endswith('.pdf'):
                count = 0
                with open(file_name, 'rb') as fh:
                    for page in PDFPage.get_pages(fh, 
                                                caching=True,
                                                check_extractable=True):
                        count += 1
                return count
            else:
                return None
    except PDFSyntaxError:
        return None

def extract_text_from_docx(doc_path):
    '''
    Helper function to extract plain text from .docx files

    :param doc_path: path to .docx file to be extracted
    :return: string of extracted text
    '''
    try:
        temp = docx2txt.process(doc_path)
        text = [line.replace('\t', ' ') for line in temp.split('\n') if line]
        return ' '.join(text)
    except KeyError:
        return ' '

def extract_text_from_doc(doc_path):
    '''
    Helper function to extract plain text from .doc files

    :param doc_path: path to .doc file to be extracted
    :return: string of extracted text
    '''
    try:
        temp = textract.process(doc_path).decode('utf-8')
        text = [line.replace('\t', ' ') for line in temp.split('\n') if line]
        return ' '.join(text)
    except KeyError:
        return ' '

def extract_text(file_path, extension):
    '''
    Wrapper function to detect the file extension and call text extraction function accordingly

    :param file_path: path of file of which text is to be extracted
    :param extension: extension of file `file_name`
    '''
    text = ''
    if extension == '.pdf':
        for page in extract_text_from_pdf(file_path):
            text += ' ' + page
    elif extension == '.docx':
        text = extract_text_from_docx(file_path)
    elif extension == '.doc':
        if os.name == 'nt':
            return ' '
        text = extract_text_from_doc(file_path)

    birth_year_regex(text)
    return text

def extract_entity_sections_grad(text):
    '''
    Helper function to extract all the raw text from sections of resume specifically for 
    graduates and undergraduates

    :param text: Raw text of resume
    :return: dictionary of entities
    '''
    text_split = [i.strip() for i in text.split('\n')]
    # sections_in_resume = [i for i in text_split if i.lower() in sections]
    entities = {}
    key = False
    for phrase in text_split:
        #print(phrase)
        if len(phrase) == 1:
            p_key = phrase
        else:
            p_key = set(phrase.lower().split()) & set(cs.RESUME_SECTIONS_GRAD)
        try:
            p_key = list(p_key)[0]
        except IndexError:
            pass
        if p_key in cs.RESUME_SECTIONS_GRAD:
            entities[p_key] = []
            key = p_key
        elif key and phrase.strip():
            entities[key].append(phrase)
    
    return entities

def get_total_experience(experience_list):
    '''
    Wrapper function to extract total months of experience from a resume
 
    :param experience_list: list of experience text extracted
    :return: total months of experience
    '''
    exp_ = []
    for line in experience_list:
        experience = re.search('(?P<fmonth>\w+.\d+)\s*(\D|to)\s*(?P<smonth>\w+.\d+|present)', line, re.I)
        if experience:
            exp_.append(experience.groups())
    total_experience_in_months = sum([get_number_of_months_from_dates(i[0], i[2]) for i in exp_])
    return total_experience_in_months

def get_number_of_months_from_dates(date1, date2):
    '''
    Helper function to extract total months of experience from a resume

    :param date1: Starting date
    :param date2: Ending date
    :return: months of experience from date1 to date2
    '''
    if date2.lower() == 'present':
        date2 = datetime.now().strftime('%b %Y')
    try:
        if len(date1.split()[0]) > 3:
            date1 = date1.split()
            date1 = date1[0][:3] + ' ' + date1[1] 
        if len(date2.split()[0]) > 3:
            date2 = date2.split()
            date2 = date2[0][:3] + ' ' + date2[1]
    except IndexError:
        return 0
    try: 
        date1 = datetime.strptime(str(date1), '%b %Y')
        date2 = datetime.strptime(str(date2), '%b %Y')
        months_of_experience = relativedelta.relativedelta(date2, date1)
        months_of_experience = months_of_experience.years * 12 + months_of_experience.months
    except ValueError:
        return 0
    return months_of_experience

def extract_entity_sections_professional(text):
    '''
    Helper function to extract all the raw text from sections of resume specifically for 
    professionals

    :param text: Raw text of resume
    :return: dictionary of entities
    '''
    text_split = [i.strip() for i in text.split('\n')]
    entities = {}
    key = False
    for phrase in text_split:
        if len(phrase) == 1:
            p_key = phrase
        else:
            p_key = set(phrase.lower().split()) & set(cs.RESUME_SECTIONS_PROFESSIONAL)
        try:
            p_key = list(p_key)[0]
        except IndexError:
            pass
        if p_key in cs.RESUME_SECTIONS_PROFESSIONAL:
            entities[p_key] = []
            key = p_key
        elif key and phrase.strip():
            entities[key].append(phrase)
    return entities

def extract_email(text):
    '''
    Helper function to extract email id from text

    :param text: plain text extracted from resume file
    '''
    email = re.findall("([^@|\s]+@[^@]+\.[^@|\s]+)", text)
    if email:
        try:
            return email[0].split()[0].strip(';')
        except IndexError:
            return None

#Made by Vishal Sharma...30/7/2019
def show_tokens(text):
    cv_tokens_list=[]
    cv_tokens_list.clear()
    for token in text:
        cv_tokens_list.append(token.text)
    
    return cv_tokens_list

#Made by Vishal Sharma...30/7/2019
def show_tokens_nlp(text):
    doc=nlp(text)
    for token in doc:
        cv_tokens_list_nlp.append(token.text)

    return cv_tokens_list_nlp

#Made by Vishal Sharma...30/7/2019
def show_ents(text):
    cv_date_list=[]
    if text.ents:
        for ent in text.ents:
            #print(ent.text,' - ',ent.label_,' - ',spacy.explain(ent.label_))
            cv_entity_list.append(ent.text)       
    else:
        print('No Entities found')

    #print('All entities : ')
    #print(cv_entity_list)  
    return cv_entity_list

#Made by Vishal Sharma...30/7/2019
def show_ents_date(text):
    cv_date_list=[]
    if text.ents:
        for ent in text.ents:
            if ent.label_=='DATE':
                cv_date_list.append(ent.text)
            
    else:
        print('No Date Entities found')
        
    return cv_date_list

#Made by Vishal Sharma...30/7/2019
def show_noun_chunks(text):
    if text.noun_chunks:
        for chunk in text.noun_chunks:
            #print(chunk.text)
            cv_noun_list.append(chunk.text)
    else:
        print('No Noun found')
    return cv_noun_list

#Made by Vishal Sharma...30/7/2019
def extract_name(nlp_text, matcher):
    '''
    Helper function to extract name from spacy nlp text
    :param nlp_text: object of `spacy.tokens.doc.Doc`
    :param matcher: object of `spacy.matcher.Matcher`
    :return: string of full name
    '''
    final_name=' '
    name_catch_token=[]
    pattern = [cs.NAME_PATTERN]
    
    matcher.add('NAME', None, *pattern)
    # print(nlp_text)
    matches = matcher(nlp_text)
    # print(matches)
    name_catch_token.clear()
    name_catch_token=show_tokens(nlp_text)
  

    for i in range(len(name_catch_token)):
        if name_catch_token[i].lower() in indianNames:
            final_name=name_catch_token[i]+' '+name_catch_token[i+1]
            if name_catch_token[i+2].lower() in indianNames:
                final_name=final_name+' '+name_catch_token[i+2]     #for taking third name 
            break
        else:
            final_name='NA'
            
    # print(final_name)
    # get_first_name(final_name,nlp_text)
        
    return final_name
    
#Made by Vishal Sharma...30/7/2019
def get_first_name(full_name,nlp_text):

    # print('aara hai kya ', full_name)

    fist_name=' '
    middle_name=' '
    last_name=' '
    first_name_new=' '
    name_full=nlp(full_name)
    get_name=[]
    name_tokens_list=[]

    name_tokens_list.clear()
    for tokens in name_full:
        name_tokens_list.append(tokens.text)
    # print(name_tokens_list)
    # print(len(name_tokens_list))
    if len(name_tokens_list)==2:
        fist_name=name_tokens_list[0]
        get_name.append(fist_name)
        last_name=name_tokens_list[1]
        get_name.append(get_father_name(nlp_text))
        get_name.append(last_name)
    elif len(name_tokens_list)==3:
        fist_name=name_tokens_list[0]
        # print(fist_name)
        middle_name=name_tokens_list[1]
        # print(middle_name)
        first_name_new=name_tokens_list[0]+' '+name_tokens_list[1]
        # print(first_name_new)
        get_name.append(first_name_new)
        get_name.append(get_father_name(nlp_text))
        last_name=name_tokens_list[2]
        get_name.append(last_name)

    return get_name

def get_father_name(nlp_text):

    father_name=' '
    name_catch_token=[]
   
    name_catch_token.clear()
    name_catch_token=show_tokens(nlp_text)
    count_j=0
    count_token=len(name_catch_token)-1
  

    for i in range(len(name_catch_token)):
        # print('out : ',name_catch_token[i])
        similar_father=fuzz.ratio(name_catch_token[i].lower(),'father')
        # print(similar_father)
        if similar_father>=90:
            # print('in : ',name_catch_token[i])
            for j in range(i+2, i+10):
                if name_catch_token[j].lower() in indianNames:
                    father_name=name_catch_token[j]
                    break

                if j>=count_token:
                    count_j=1
                    break

        if count_j==1 or father_name!=' ':
            break                    
            
    if father_name==' ':
        father_name='NA'
    

    return father_name
  

#Made by Vishal Sharma...30/7/2019
def get_gender(text):
    gender=' '
    similar_percent_gender=0
    similar_percent_sex=0
    
    check_gender=show_tokens(text)
    try:
        for i in range(len(check_gender)):
            similar_percent_gender=fuzz.ratio(check_gender[i].lower().strip(), 'gender')
            similar_percent_sex=fuzz.ratio(check_gender[i].lower().strip(), 'sex')
            if similar_percent_gender>=90 or similar_percent_sex>=90:
                for j in range(i+1,i+10):
                   if check_gender[j].lower()=='male':
                        gender='Male'
                        break
                   elif check_gender[j].lower()=='female':
                        gender='Female'
                        break

        if gender==' ':
            gender='NA'
    except:
        gender='Check karo'

    #print(f'Gender : {gender}')
    return gender

#Made by Vishal Sharma...30/7/2019
def get_nationality(text):
    nationality=' '
    similar_percent_nationality=0
    
    check_nationality=show_tokens(text)
    try:
    
        for i in range(len(check_nationality)):
            similar_percent_nationality=fuzz.ratio(check_nationality[i].lower().strip(), 'nationality')
            if similar_percent_nationality>=90:
                for j in range(i+1,i+10):
                   if check_nationality[j].lower()=='indian':
                        nationality='Indian'
                        break
            
        if nationality==' ':
            nationality='NA'
    except:
        nationality='Check karo'

    #print(f'Gender : {gender}')
    return nationality

#Made by Vishal Sharma...30/7/2019
def get_maritial_status(text):
    marital_status=' '
    similar_percent_marital=0
    check_status=[]
    count_j=0
    check_status=show_tokens(text)
    check_tokens=len(check_status)-1
    try:
        
        for i in range(len(check_status)):
            similar_percent_marital_1=fuzz.ratio(check_status[i].lower().strip(), 'marital')
            similar_percent_marital_2=fuzz.ratio(check_status[i].lower().strip(), 'maritalstatus')
            if similar_percent_marital_1>=90 or similar_percent_marital_2>=90:
                for j in range(i+1,i+20):
                    if check_status[j].lower() in marital_status_list:
                        marital_status=check_status[j]
                        break

                    if j>=check_tokens:
                        count_j=1
                        break

        if marital_status==' ' or count_j==1:
            marital_status='NA'
    except:
        
        marital_status='Check karo'
        
    #print(f'Maritial Status : {maritial_status}')
    return marital_status

#Made by Vishal Sharma...30/7/2019
def get_passport_number(text):
    passport_number='NA'
    # passport_number = re.findall("^(?!^0+$)[a-zA-Z0-9]{3,20}$", text)   #check regex valid/invalid?
    # print(f'Passport Number : {passport_number}')
    return passport_number

#Made by Vishal Sharma...30/7/2019
def extract_language(nlp_text, noun_chunks, language_file=None):
    '''
    Helper function to extract skills from spacy nlp text

    :param nlp_text: object of `spacy.tokens.doc.Doc`
    :param noun_chunks: noun chunks extracted from nlp text
    :return: list of skills extracted
    '''
    languages_set=[]
    similar_percent_language=0
    data = pd.read_csv(os.path.join(os.path.dirname(__file__), 'Language_Resume.csv'), encoding = 'unicode_escape')
    languages = list(data.columns.values)
    check_language=show_tokens(nlp_text)
    check_token=len(check_language)-1
    count_j=0
    try:
        
        for i in range(len(check_language)):
            similar_percent_language=fuzz.ratio(check_language[i].lower().strip(), 'languages')
            if similar_percent_language>=90:
                for j in range(i+2,i+30):
                    if check_language[j].lower() in languages:
                        #print(check_language[j].lower())
                        languages_set.append(check_language[j])
                    if j>=check_token:
                        count_j=1
                        break

            if len(languages_set)>0 or count_j==1:
                break
    except:
        
       languages_set.append('Check karo') 

    #print(languages_set)

    #print(f'Language : {[i.capitalize() for i in set([i.lower() for i in languages_set])]}')
    return [i.capitalize() for i in set([i.lower() for i in languages_set])]

#Made by Vishal Sharma...31/7/2019
def extract_hobbies(nlp_text, noun_chunks, hobbies_file=None):
    '''
    Helper function to extract skills from spacy nlp text

    :param nlp_text: object of `spacy.tokens.doc.Doc`
    :param noun_chunks: noun chunks extracted from nlp text
    :return: list of skills extracted
    '''
    hobbies_set=[]
    count_j=0
    similar_percent_hobbies=0
    similar_percent_interest=0
    data = pd.read_csv(os.path.join(os.path.dirname(__file__), 'Hobbies_Resume.csv'), encoding = 'unicode_escape')
    hobbies = list(data.columns.values)
    check_hobbies=show_tokens(nlp_text)
    check_tokens=len(check_hobbies)-1
    #print(check_hobbies)

    try:

        for i in range(len(check_hobbies)):
            similar_percent_hobbies=fuzz.ratio(check_hobbies[i].lower().strip(), 'hobbies')
            similar_percent_interest=fuzz.ratio(check_hobbies[i].lower().strip(), 'interests')

            if similar_percent_hobbies>=90 or similar_percent_interest>=90:
                # print('Check ',check_hobbies[i])
                for j in range(i+1,i+40):
                    #   print(check_hobbies[j])
                    if check_hobbies[j].lower() in hobbies:
                        # print(check_hobbies[j].lower())
                        hobbies_set.append(check_hobbies[j])

                    if j>=check_tokens:
                        count_j=count_j+1
                        break

                

            if len(hobbies_set)>0 or count_j==1:
                break
    except:
        
       hobbies_set.append('Check karo') 

    #print(hobbies_set)

    #print(f'Hobbies : {[i.capitalize() for i in set([i.lower() for i in hobbies_set])]}')
    return [i.capitalize() for i in set([i.lower() for i in hobbies_set])]

def birth_year_regex(text):
    reg_ex='[1-2][0-9][0-9][0-9]'
    x = re.findall(reg_ex, text)
    # print(x)
    return x

#Made by Vishal Sharma...31/7/2019
def extract_date_of_birth(nlp_text, text):

    count=0
    cnt=0
    date_of_birth='NA'
    final_dob=' '
    ent_break=[]
    date_of_birth_entity=[]
    date_of_birth_verify=' '
    index_value=0
    dob_ents=show_ents_date(nlp_text)
    year_regex=birth_year_regex(text)
    birth_str=' '

    # print(dob_ents)

    tokens_list=show_tokens(nlp_text)
    try:

        for i in range(len(tokens_list)):
            # print(tokens_list[i].lower())
            if tokens_list[i].lower()=='birth' or tokens_list[i].lower()=='dob' or tokens_list[i].lower()=='d.o.b' or tokens_list[i].lower()=='d.o.b.':
                index_value=i
                # print(tokens_list[i].lower())   
                for j in range(i+1,i+10):
                    for l in range(len(dob_ents)):
                        ent_break.clear()
                        ent_break=show_tokens_nlp(dob_ents[l])
                        #print(ent_break)
                        for k in range(len(ent_break)):
                            if tokens_list[j].lower()==ent_break[k]:
                                date_of_birth_verify=dob_ents[l]
                                count=1
                                break
                    if count==1:
                        break
                if count==1:
                    break
            if count==1:
                break

        if date_of_birth_verify!=' ':
            for a in range(index_value+1,index_value+10):
                date_of_birth_entity=show_tokens_nlp(date_of_birth_verify)
                last_token_index=len(date_of_birth_entity)-1
                #print(tokens_list[a])
                final_dob=final_dob+str(tokens_list[a])+' '
                if tokens_list[a]==date_of_birth_entity[last_token_index]:
                    #print(tokens_list[a])
                    break
        # print('dekh ek baar toh: ',final_dob)
        if final_dob==' ':
            # print('aaya kya')
            for i in range(len(tokens_list)):
                # print(tokens_list[i].lower())
                if tokens_list[i].lower()=='birth' or tokens_list[i].lower()=='dob' or tokens_list[i].lower()=='d.o.b' or tokens_list[i].lower()=='d.o.b.':
                    index_value=i
                    for j in range(i+2,i+10):
                        if tokens_list[j] not in year_regex:
                            final_dob=final_dob+tokens_list[j]+' '
                        else:
                            final_dob=final_dob+tokens_list[j]+' '
                            break
                        
                if final_dob!=' ':
                    break

        if final_dob==' ':
            final_dob='NA'

    except:
         
        final_dob='Check karo'
    # print(f'Date of Birth : {final_dob}')

    # extract_no_of_companies_worked_for(nlp_text)

    return final_dob

def unique(list1): 
  
    # intilize a null list 
    unique_list = [] 
      
    # traverse for all elements 
    for x in list1: 
        # check if exists in unique_list or not 
        if x not in unique_list: 
            unique_list.append(x) 

    return unique_list
       

# Made by Vishal Sharma...9/8/2019
def extract_no_of_companies_worked_for(nlp_text, noun_chunks, hobbies_file=None):
    '''
    companies_set=[]
    similar_percent=0
    data = pd.read_csv(os.path.join(os.path.dirname(__file__), 'company.csv'), encoding = 'unicode_escape')
    companies=list(data.columns.values)
    check_companies=show_ents(nlp_text)
    check_companies_token=show_tokens(nlp_text)
    # print(check_companies)

    for i in range(len(check_companies)):
        #print(check_companies[i])
        if check_companies[i].lower() != 'technologies':
            for j in range(len(companies)):
                # print(companies[j])
                similar_percent=fuzz.ratio(check_companies[i].lower().strip(), companies[j].strip())
                
                print('Resume:',check_companies[i].lower().strip())
                print('Excel:',companies[j].strip())
                print(similar_percent)
                
                if similar_percent>=80:
                    
                    print('Resume:',check_companies[i].lower().strip())
                    print('Excel:',companies[j].strip())
                    print('similarity:',similar_percent)
                    
                    companies_set.append(check_companies[i])

    for i in range(len(check_companies_token)):
        for j in range(len(companies)):
            similar_percent=fuzz.ratio(check_companies_token[i].lower().strip(), companies[j].strip())
            
            print('Resume:',check_companies[i].lower().strip())
            print('Excel:',companies[j].strip())
            print(similar_percent)
            
            if similar_percent>=100:
                
                print('Resume:',check_companies[i].lower().strip())
                print('Excel:',companies[j].strip())
                print('similarity:',similar_percent)
                
                companies_set.append(check_companies_token[i])
                    
                   
    # print(unique(companies_set))
    # print(len(companies_set))
    
    print(companies_set)
    return len(unique(companies_set))
    '''    
    return '0'                                     
    '''
    print(f'Hobbies : {[i.capitalize() for i in set([i.lower() for i in companies_set])]}')
    return [i.capitalize() for i in set([i.lower() for i in companies_set])]
    '''


def extract_mobile_number(text):
    '''
    Helper function to extract mobile number from text

    :param text: plain text extracted from resume file
    :return: string of extracted mobile numbers
    '''
    # Found this complicated regex on : https://zapier.com/blog/extract-links-email-phone-regex/
    phone = re.findall(re.compile(r'(?:(?:\+?([1-9]|[0-9][0-9]|[0-9][0-9][0-9])\s*(?:[.-]\s*)?)?(?:\(\s*([2-9]1[02-9]|[2-9][02-8]1|[2-9][02-8][02-9])\s*\)|([0-9][1-9]|[0-9]1[02-9]|[2-9][02-8]1|[2-9][02-8][02-9]))\s*(?:[.-]\s*)?)?([2-9]1[02-9]|[2-9][02-9]1|[2-9][02-9]{2})\s*(?:[.-]\s*)?([0-9]{7})(?:\s*(?:#|x\.?|ext\.?|extension)\s*(\d+))?'), text)
    if phone:
        number = ''.join(phone[0])
        if len(number) > 10:
            return '+' + number
        else:
            return number

#updated by Vishal Sharma 11/8/2019
def extract_address(nlp_text, noun_chunks):
    tokens = [token.text for token in nlp_text if not token.is_stop]
    similar_percent_address=0
    data = pd.read_csv(os.path.join(os.path.dirname(__file__), 'states.csv'), encoding = 'unicode_escape')
    states_list = list(data.columns.values)
    data1 = pd.read_csv(os.path.join(os.path.dirname(__file__), 'cities.csv'), encoding = 'unicode_escape')
    cities_list = list(data1.columns.values)
    address_set = []
    address = ' '
    count_k=0
    count_j=0
    count_b=0
    count_c=0
    check_count=0
    count_token=len(tokens)-1

    try:

        for a in range(len(tokens)):
            # print(tokens[a])
            if check_count==1:
                break
            if tokens[a].lower() in indianNames:
                check_count=check_count+1
                for b in range(a+2, a+20):
                    # print(tokens[b].lower())
                    # print('phela out : ',tokens[b].lower())
                    if tokens[b].lower() in cities_list:
                        # print('phela in : ',tokens[b].lower().strip())
                        for c in range(a+2, a+20):
                            # print('address out : ',tokens[c].lower())
                            if tokens[c].lower() not in cities_list and tokens[c].lower() not in states_list:
                                # print('address in: ',tokens[c].lower())
                                address=address+tokens[c]+' '
                            else:
                                break

                            if c>=count_token:
                                count_c=count_c+1
                                break

                            
                    elif address!=' ':
                        break

                    if b>=count_token:
                        count_b=count_b+1
                        break

                if address!=' ':
                    break
                elif count_b==1 or count_c==1:
                    break           
                    
        if address==' ':
            for i in range(len(tokens)):
                similar_percent_address=fuzz.ratio(tokens[i].lower().strip(), 'address')
                if similar_percent_address>=90:
                    # print(tokens[i].lower().strip())
                    for j in range(i+2, i+20):
                        # print(tokens[j].lower().strip())
                        if tokens[j].lower() in cities_list:
                            # print(tokens[j].lower().strip())
                            for k in range(i+2, i+20): 
                                if tokens[k].lower() not in cities_list and tokens[k].lower() not in states_list:
                                    address=address+tokens[k]+' '
                                else:
                                    break
                                
                                if k>=count_token:
                                    count_k=count_k+1
                                    break
                            

                        if j>=count_token:
                            count_j=count_j+1
                            break
                        
                        

            
                        
                    if address!=' ':
                        break
                    elif count_k==1:
                        break
                    elif count_j==1:
                        break

        if address==' ':
            address='NA'
    except:
        address='Check karo'
            
    return address

#updated by Vishal Sharma 11/8/2019
def extract_pin_exceptional(nlp_text, noun_chunks,found_pins):
    tokens = [token.text for token in nlp_text if not token.is_stop]
    # print(tokens)
    pin_set = []
    pin_count = 0
    j=1
    flag = 0
    count = 0
    pincode=' '
    similar_percent_pincode = 0
    count_token=len(tokens)-1
    
    # print('found pincodes: '+str(found_pins))
    try:

        for i in range(len(tokens)):
            similar_percent_pincode=fuzz.ratio(tokens[i].lower().strip(), 'address')
            if similar_percent_pincode>=90:
                # print(tokens[i].lower().strip())
                for j in range(i+1,i+20):
                    # print(tokens[j].lower().strip())
                    for k in range(len(found_pins)):
                        if found_pins[k] in tokens[j]:
                            #print('dekh ',tokens[j].lower().strip())
                            pincode=found_pins[k]
                            count=count+1
                            break
            
                    if count==1:
                        break
                    elif j>=count_token:
                        break

            if count==1:
                break

    except:

        pincode='Check karo'
            
    #return [i.capitalize() for i in set([i.lower() for i in pin_set])]
    return pincode

def extract_cities_exceptional(nlp_text, noun_chunks,found_cities):
    
    tokens = [token.text for token in nlp_text if not token.is_stop]
    city_set = []
    city_count = 0
    j=1
    count = 0
    #print('found cities'+str(found_cities))
    for i in range(0,len(tokens)-1):
        while tokens[i].lower().strip() == 'address' and count < 15:
            count += 1
            #print(tokens[i+j])
            try:
                if found_cities[city_count].lower().strip() in tokens[i+j].lower().strip():
                    #print('append hua'+str(tokens[i+j]))
                    city_set.append(found_cities[city_count])
                    break
            except:
                break
            j += 1
            
            if count == 15:
                city_count += 1
                count = 0
                j = 1
    return [i.capitalize() for i in set([i.lower() for i in city_set])]        
    

def extract_cities(nlp_text, noun_chunks):
    tokens = [token.text for token in nlp_text if not token.is_stop]
    data = pd.read_csv(os.path.join(os.path.dirname(__file__), 'cities.csv'), encoding = 'unicode_escape')
    cities_list = list(data.columns.values)
    #print(cities_list)
    similar_percent_cities=0
    city_name=' '
    city_set = []
    count=0
    count_token=len(tokens)-1
    check_token=0

    try:
        
        for i in range(len(tokens)):
            if tokens[i].lower() in indianNames:
                if check_token==0:
                    check_token=check_token+1
                    # print(tokens[i].lower())
                    for j in range(i+2, i+20):
                        # print(tokens[j].lower())
                        if tokens[j].lower() in cities_list:
                            city_name=tokens[j]

                        if j>=count_token:
                            break

                        if city_name!=' ':
                            break

                    if city_name!=' ':
                            break
                else:
                    break
                   
        if city_name==' ':   
            for i in range(len(tokens)):
                similar_percent_cities=fuzz.ratio(tokens[i].lower().strip(), 'address')
                if similar_percent_cities>=90:
                    #print(tokens[i].lower().strip())
                    for j in range(i+1,i+20):
                        #print(tokens[j].lower().strip())
                        for k in range(len(cities_list)):
                            #print(tokens[j].lower().strip())
                            #print('city :',cities_list[k])
                            if tokens[j].lower() == cities_list[k]:
                                #print('dekh ',tokens[j].lower().strip())
                                #print(cities_list[k])
                                city_name=tokens[j]
                                #print(city_name)
                                count=count+1
                                break
                
                        if count==1:
                            break
                        elif j>=count_token:
                            break

                if count==1:
                    break

        if city_name == ' ':
            city_name='NA'

    except:
        city_name='Check karo'
            
    return city_name
        
def extract_state(nlp_text, noun_chunks):
    tokens = [token.text for token in nlp_text if not token.is_stop]
    data = pd.read_csv(os.path.join(os.path.dirname(__file__), 'states.csv'), encoding = 'unicode_escape')
    states_list = list(data.columns.values)
    state_set = []
    state_name=' '
    similar_percent_state=0
    count=0
    count_token=len(tokens)-1
    check_token=0

    try:
        
        for i in range(len(tokens)):
            if tokens[i].lower() in indianNames:
                # print('Indianname ',tokens[i])
                if check_token==0:
                    check_token=check_token+1
                    for j in range(i+2, i+20):
                        # print(tokens[j].lower())
                        if tokens[j].lower() in states_list:
                            state_name=tokens[j]

                        if state_name!=' ':
                            break

                        if j>=count_token:
                            break

                    if state_name!=' ':
                            break
                else:
                    break
            

        if state_name==' ':
            for i in range(len(tokens)):
                similar_percent_state=fuzz.ratio(tokens[i].lower().strip(), 'address')
                if similar_percent_state>=90:
                    #print(tokens[i].lower().strip())
                    for j in range(i+1,i+30):
                       # print(tokens[j].lower().strip())
                        for k in range(len(states_list)):
                            if tokens[j].lower().strip() == states_list[k].lower().strip():
                                state_name=tokens[j]
                                count=count+1
                                break
                            elif tokens[j].lower()=='uttar' or tokens[j].lower()=='andra' or tokens[j].lower()=='madhya' or tokens[j].lower()=='arunachal' or tokens[j].lower()=='himachal' or tokens[j].lower()=='tamil' or tokens[j].lower()=='west':
                                state_name=tokens[j]+' '+tokens[j+1]
                                count=count+1
                                break
                            elif tokens[j].lower()=='andaman':
                                 state_name=='Andaman & Nicobar Islands'
                                 count=count+1
                                 break
                            elif tokens[j].lower()=='dadra':
                                 state_name='Dadra & Nagar Haveli'
                                 count=count+1
                                 break
                            elif tokens[j].lower()=='daman':
                                 state_name='Daman & Diu'
                                 count=count+1
                                 break
                            elif tokens[j].lower()=='jammu':
                                 state_name='Jammu & Kashmir'
                                 count=count+1
                                 break

                        if count==1:
                            break
                        elif j>=count_token:
                            break

                if count==1:
                    break

        if state_name == ' ':
            state_name='NA'

    except:
        
        state_name='Check karo'
            
    return state_name
    

def extract_pin(nlp_text, noun_chunks):
    tokens = [token.text for token in nlp_text if not token.is_stop]
    data = pd.read_csv(os.path.join(os.path.dirname(__file__), 'pincodes.csv'), encoding = 'unicode_escape')
    pincodes = list(data.columns.values)
    pin_set = []
        

    for  i in range(0,len(tokens)-1):
        for j in range(0,len(pincodes)-1):
            if pincodes[j] in tokens[i].lower().strip():
                pin_set.append(pincodes[j])

    '''    
    for i in range(0,len(noun_chunks)-1):
        for j in range(0,len(pincodes)-1):
            if pincodes[j] in noun_chunks[i]:
                 pin_set.append(noun_chunks[i])
            
            noun_chunks[i] = noun_chunks[i].text.lower().strip()
            if noun_chunks[i] in pincodes:
                pin_set.append(noun_chunks[i])
    '''
    #print('ye bhi address hai'+str(address_set))
    return [i.capitalize() for i in set([i.lower() for i in pin_set])]
    
def extract_skills(nlp_text, noun_chunks):
    '''
    Helper function to extract skills from spacy nlp text

    :param nlp_text: object of `spacy.tokens.doc.Doc`
    :param noun_chunks: noun chunks extracted from nlp text
    :return: list of skills extracted
    '''
    tokens = [token.text for token in nlp_text if not token.is_stop]
    data = pd.read_csv(os.path.join(os.path.dirname(__file__), 'skills.csv'), encoding = 'unicode_escape') 
    skills = list(data.columns.values)
    skillset = []
    # check for one-grams
    for token in tokens:
        if token.lower() in skills:
            skillset.append(token)
    
    # check for bi-grams and tri-grams
    for token in noun_chunks:
        token = token.text.lower().strip()
        if token in skills:
            skillset.append(token)
    return [i.capitalize() for i in set([i.lower() for i in skillset])]

def cleanup(token, lower = True):
    if lower:
       token = token.lower()
    return token.strip()


def f7(seq):
    seen = set()
    seen_add = seen.add
    return [x for x in seq if not (x in seen or seen_add(x))]


def rem_dup(x):
    return list(dict.fromkeys(x))


def extract_education(nlp_text,nlp_text1,resume,dob):
    count = 0
    edu = []
    deg = []
    temp_deg = temp_year = temp_marks = ''
    tokens = [token.text for token in nlp_text1]
    data = pd.read_csv(os.path.join(os.path.dirname(__file__), 'degrees.csv'),encoding = 'unicode_escape') 
    degrees = list(data.columns.values)



    try:
        for i in range(0,len(tokens)-1):
            while count < 54 and ('academi' in tokens[i].lower() or  'education' in tokens[i].lower()) :
                try:
                    tokens[i+count] = tokens[i+count].replace('(', ' ')
                    tokens[i+count] = tokens[i+count].replace(')', ' ')
                    if tokens[i+count].lower().strip() == 'ms':
                        if tokens[i+count+1].lower().strip() == 'excel' or tokens[i+count+1].lower().strip() == 'office' or tokens[i+count+1].lower().strip() == 'azure' or tokens[i+count+1].lower().strip() == '-':
                            tokens[i+count] = 'MSOffice'
                    if (' ' in str(tokens[i+count]) and len(str(tokens[i+count])) > 2) or (',' in str(tokens[i+count]) and len(str(tokens[i+count])) > 2):
                        spltted = tokens[i+count].split(',')
                        edu.append(spltted[0])
                        edu.append(spltted[1])
                        
                    edu.append(tokens[i+count])
                    count += 1
                except:
                    break

        #print(edu)
        
        try:
            df = read_pdf(resume)
            if df == None:
                df = pd.DataFrame()
        except pd.errors.ParserError:
            print('continue')
            df = pd.DataFrame()
        except subprocess.CalledProcessError:
            print('continue docx Found')
            df = pd.DataFrame()
        except:
            print('continue1')
            df = read_pdf(resume)
            #print(df)

            
        cols = list(df.columns.values)
        flag = 0
        for i in range(len(cols)):
            cols[i] = str(cols[i])
            cols[i] = cols[i].lower().strip()
            if 'year' in cols[i]:
                flag = 1
            # print(cols[i])
        
        if not df.empty and df.shape[1]>=3 and flag == 1 :
            #print(df)
            cols = list(df.columns.values)
            year_col = ''
            for i in range(0,len(cols)):
                if 'year' in cols[i].lower().strip():
                    year_col = cols[i]
                    break
            if year_col != '':
                years = list(df[year_col])
            else:
                years = []
            for i in range(0,len(years)):
                if len(str(years[i])) > 4:
                    years[i] = years[i][-4:]
            

            deg_col = ''
            for i in range(0,len(cols)):
                if 'educ' in cols[i].lower().strip() or 'qualifi' in cols[i].lower().strip() or 'degree' in cols[i].lower().strip() or 'course' in cols[i].lower().strip() or 'exam' in cols[i].lower().strip():
                    deg_col = cols[i]
                    break
            if deg_col != '':     
                true_edu = list(df[deg_col])
            else:
                true_edu = []
            

            mark_col = ''
            for i in range(0,len(cols)):
                if 'mark' in cols[i].lower().strip() or 'percent' in cols[i].lower().strip() or 'score' in cols[i].lower().strip():
                    mark_col = cols[i]
                    break
            if mark_col != '':     
                marks = list(df[mark_col])
            else:
                marks = []
            
            uni_col = ''
            for i in range(0,len(cols)):
                if 'uni' in cols[i].lower().strip() or 'board' in cols[i].lower().strip() or 'insti' in cols[i].lower().strip():
                    uni_col = cols[i]
                    break
            if uni_col != '':
                uni = list(df[uni_col])
            else:
                uni = []

            
            for i in range(0,len(years)):
                for j in range(0,len(years)):
                    #print(j)
                    years[j] = re.sub(r'[?|$|.|!|,|-]', r'', str(years[j]))    
                    try:
                        if not str(years[j]).isdigit() and not is_date(years[j]):
                            
                            del years[j]
                            del marks[j]
                            del true_edu[j]
                            del uni[j]
                            break
                    except:
                        break
                
            final_edu = []
            final_edu.append([true_edu,years,marks,uni])
            # print(final_edu)
            
        else:
            
            count = 0
            true_deg = []
            edu_count = 0
            for i in range(0,len(edu)):
                true_edu = edu[i].lower().strip()
                education = edu[i].lower().strip()
                for j in range(0,5):
                    
                    try:
                        education = re.sub(r"[?|$|.|!|,|']", r'', education)
                        if education in degrees:
                            #print(education)
                            if education == 'ssc':
                                temp = education
                                break
                            if education not in deg or education == 'cbse':
                                deg.append(education)
                                true_deg.append(true_edu.strip())
                                #print('hua')
                                break
                            '''
                            else:
                                print('nhi hua')
                            '''
                        else:
                            education += edu[i+j+1].lower()
                            true_edu = true_edu + ' ' + edu[i+j+1].lower().strip()
                    except:
                        break
            
            for i in range(0,len(true_deg)):
                if true_deg[i] == 'cbse':
                    edu_count += 1

            if edu_count < 2 and ('ssc' in edu or 's.s.c'  in edu or 's.s.c.'  in edu or 'SSC'  in edu or 'S.S.C'  in edu or 'S.S.C.'  in edu):
                true_deg.append('ssc')
                deg.append('ssc')
            
            # print(true_deg)
            del_item = []
                      

            years = []
            for i in range(0,len(edu)):
                year = edu[i].lower().strip()
                year = year.replace('|','')
                #print(year)
                if i+2 < len(edu):
                    if str(edu[i+1].lower().strip()) == '-' and re.match(r'(((20|19)(\d{2})))', str(edu[i+2].lower().strip())):               
                        year = 'galat h mat kar'
                        print('nhi hua')
                    elif '-' in str(edu[i+1].lower().strip()):
                        year = 'galat h mat kar'
                        
                # print(year)
                      
                if is_date(year) and not re.match(r'^\d{0,2}(\.\d{1,4})? *?$', str(year)):
                    if hasNumbers(year):
                        year = parser.parse(year).year
                    if re.match(r'(((20|19)(\d{2})))', str(year)):
                        years.append(year)

                
            for i in range(len(years)):
                if str(years[i]) in dob:
                    del years[i]

         
                    
            # print(years)

            marks = []
            for i in range(0,len(edu)):
                mark = edu[i].lower().strip()
                if re.match(r'^\d{0,2}(\.\d{1,4})? *?$', str(mark)) or str(mark) == 'distinction' :
                    if edu[i-1].lower().strip() != '/':
                        marks.append(mark)
                    else:
                        print('wrong')

            
            marks = ' '.join(marks).split()
            if len(years) >= 1:
                del marks[len(years):]
            elif len(deg) >= 1:
                del marks[len(deg):]
            marks = rem_dup(marks)
            
            for i in range(0,len(marks)):
                try:
                    if float(marks[i]) > 10 and float(marks[i]) < 35:
                        del marks[i]
                except:
                    print('distinction waala h')

        
            final_edu = []
            final_edu.append([true_deg,years,marks])


    except:
        final_edu = []
        final_edu.append('Check karo')
    
    return final_edu
    
    
def extract_experience_exceptional(nlp_text, noun_chunks):
    tokens = [token.text for token in nlp_text if not token.is_stop]
    exp_set = []
    exp_count = 0
    j=1
    flag = 0
    months = []
    years = []
    dates_1 = []

    for i in range(0,len(tokens)-1):
        #print(i,tokens[i].lower().strip())
        count = 0
        j=1
        while ('experience' in tokens[i].lower().strip() or 'duration' in tokens[i].lower().strip())  and count < 25:

            count += 1
            try:
               
                '''
                if tokens[i+j].lower().strip() in cs.MONTH:
                    months.append(tokens[i+j])
                    flag += 1
                if tokens[i+j].lower().strip() in cs.YEAR:
                    years.append(tokens[i+j]) 
                    flag += 1
                if tokens[i+j].lower().strip() in cs.DATES:
                    dates_1.append(tokens[i+j]) 
                    flag += 1
                '''
                if 'years' in tokens[i+j].lower().strip():
                    years.append(tokens[i+j-1])
                if 'months' in tokens[i+j].lower().strip():
                    months.append(tokens[i+j-1])
            
                j += 1
            except:
                break

    
    years_exp =0
    for i in range(0,len(years)):
        years_exp = years_exp + int(years[i])
    months_exp =0           
    for i in range(0,len(months)):
        months_exp = months_exp + int(months[i])
    # print("Experience : "+str(years_exp)+'Years '+str(months_exp)+'Months')
    return# [i.capitalize() for i in set([i.lower() for i in dates])]        

def extract_experience(resume_text):
    '''
    Helper function to extract experience from resume text

    :param resume_text: Plain resume text
    :return: list of experience
    '''
    wordnet_lemmatizer = WordNetLemmatizer()
    stop_words = set(stopwords.words('english'))

    # word tokenization 
    word_tokens = nltk.word_tokenize(resume_text)

    # remove stop words and lemmatize  
    filtered_sentence = [w for w in word_tokens if not w in stop_words and wordnet_lemmatizer.lemmatize(w) not in stop_words] 
    sent = nltk.pos_tag(filtered_sentence)

    # parse regex
    cp = nltk.RegexpParser('P: {<NNP>+}')
    cs = cp.parse(sent)
    
    # for i in cs.subtrees(filter=lambda x: x.label() == 'P'):
    #     print(i)
    
    test = []
    
    for vp in list(cs.subtrees(filter=lambda x: x.label()=='P')):
        test.append(" ".join([i[0] for i in vp.leaves() if len(vp.leaves()) >= 2]))

    # Search the word 'experience' in the chunk and then print out the text after it
    x = [x[x.lower().index('experience') + 10:] for i, x in enumerate(test) if x and 'experience' in x.lower()]
    return x

def get_score(_dict):
    _len = len(_dict)
    if _len >= 5:
        return 1
    elif _len < 5 and _len > 2:
        return 0.5
    elif _len  == 1:
        return 0.2
    else:
        return 0

def extract_competencies(text, experience_list):
    '''
    Helper function to extract competencies from resume text

    :param resume_text: Plain resume text
    :return: dictionary of competencies
    '''
    experience_text = ' '.join(experience_list)
    competency_dict = {}
    score = 0

    percentage = (100 // len(cs.COMPETENCIES.keys()))

    for competency in cs.COMPETENCIES.keys():
        matches = {}
        for item in cs.COMPETENCIES[competency]:
            if string_found(item, experience_text):
                if competency not in competency_dict.keys():
                    match = re.search(r'([^.|,]*' + item + '[^.|,]*)', experience_text)
                    if item not in matches.keys():
                        matches[item] = [match.group(0)]
                    else:
                        for i in match.groups():
                            matches[item].append(i)    
                    competency_dict[competency] = matches
                else:
                    match = re.search(r'([^.|,]*' + item + '[^.|,]*)', experience_text)
                    if item not in matches.keys():
                        matches[item] = [match.group(0)]
                    else:
                        for i in match.groups():
                            matches[item].append(i)
                    competency_dict[competency] = matches
                score += get_score(competency_dict[competency]) * percentage
            
    competency_dict['score'] = score
    return competency_dict

def extract_measurable_results(text, experience_list):
    '''
    Helper function to extract measurable results from resume text

    :param resume_text: Plain resume text
    :return: dictionary of measurable results
    '''

    # we scan for measurable results only in first half of each sentence
    experience_text = ' '.join([text[:len(text) // 2 - 1] for text in experience_list])
    mr_dict = {}
    experience_text_for_matching = ' '.join(experience_list)
    score = 0

    percentage = (100 // len(cs.COMPETENCIES.keys()))

    for mr in cs.MEASURABLE_RESULTS.keys():
        matches = {}
        for item in cs.MEASURABLE_RESULTS[mr]:
            if string_found(item, experience_text):
                if mr not in mr_dict.keys():
                    match = re.search(r'([^.|,]*' + item + '[^.|,]*)', experience_text_for_matching)
                    if item not in matches.keys():
                        matches[item] = [match.group(0)]
                    else:
                        for i in match.groups():
                            if i not in matches[item]:
                                matches[item].append(i) 
                    mr_dict[mr] = matches
                else:
                    match = re.search(r'([^.|,]*' + item + '[^.|,]*)', experience_text_for_matching)
                    if item not in matches.keys():
                        matches[item] = [match.group(0)]
                    else:
                        for i in match.groups():
                            if i not in matches[item]:
                                matches[item].append(i) 
                    mr_dict[mr] = matches
                score += get_score(mr_dict[mr]) * percentage
    
    mr_dict['score'] = score
    return mr_dict

def string_found(string1, string2):
    if re.search(r"\b" + re.escape(string1) + r"\b", string2):
        return True
    return False
