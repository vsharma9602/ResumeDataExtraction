import os
import utils
import spacy
import pprint
from spacy.matcher import Matcher
import multiprocessing as mp
import io

class ResumeParser(object):
    def __init__(self, resume, skills_file=None, languages_file=None, hobbies_file=None, companies_file=None):
        nlp = spacy.load('en_core_web_sm')
        self.__skills_file = skills_file
        self.__languages_file = languages_file
        self.__hobbies_file = hobbies_file
        self.__companies_file = companies_file
        self.__matcher = Matcher(nlp.vocab)
        self.__details = {
            'name'              : None,
            'full_name'         : None,
            'gender'            : None,
            'maritial_status'   : None,
            'passport_number'   : None,
            'date_of_birth'     : None,
            'email'             : None,
            'mobile_number'     : None,
            'skills'            : None,
            'nationality'       : None,
            'languages'         : None,
            'No. of companies'  : None,
            'hobbies'           : None,
            'education'         : None,
            'experience'        : None,
            'competencies'      : None,
            'measurable_results': None,
            'no_of_pages'       : None,
            'total_experience'  : None,
            'address'           : None,
            'state'             : None,
            'city'              : None,
            'pin'               : None
        }
        self.__resume      = resume
        if not isinstance(self.__resume, io.BytesIO):
            ext = os.path.splitext(self.__resume)[1].split('.')[1]
        else:
            ext = self.__resume.name.split('.')[1]
        self.__text_raw    = utils.extract_text(self.__resume, '.' + ext)
        self.__text        = ' '.join(self.__text_raw.split())
        self.__nlp         = nlp(self.__text)
        self.__noun_chunks = list(self.__nlp.noun_chunks)
        self.__get_basic_details()

    def get_extracted_data(self):
        return self.__details

    def __get_basic_details(self):
        name       = utils.extract_name(self.__nlp, matcher=self.__matcher)
        full_name  = utils.get_first_name(name, self.__nlp)
        gender     = utils.get_gender(self.__nlp)
        maritial_status = utils.get_maritial_status(self.__nlp)
        passport_number = utils.get_passport_number(self.__text_raw)
        date_of_birth = utils.extract_date_of_birth(self.__nlp, self.__text)
        email      = utils.extract_email(self.__text)
        mobile     = utils.extract_mobile_number(self.__text)
        skills     = utils.extract_skills(self.__nlp, self.__noun_chunks)
        nationality = utils.get_nationality(self.__nlp)
        languages  = utils.extract_language(self.__nlp, self.__noun_chunks, self.__languages_file)
        num_of_companies = utils.extract_no_of_companies_worked_for(self.__nlp, self.__noun_chunks, self.__companies_file)
        hobbies    = utils.extract_hobbies(self.__nlp, self.__noun_chunks, self.__hobbies_file)
        edu        = utils.extract_education([sent.string.strip() for sent in self.__nlp.sents],self.__nlp,self.__resume,date_of_birth)
        entities   = utils.extract_entity_sections_grad(self.__text_raw)
        address    = utils.extract_address(self.__nlp, self.__noun_chunks)
        states     = utils.extract_state(self.__nlp, self.__noun_chunks)
        pincodes   = utils.extract_pin(self.__nlp, self.__noun_chunks)
        cities     = utils.extract_cities(self.__nlp, self.__noun_chunks)
        experience = utils.extract_experience_exceptional(self.__nlp, self.__noun_chunks)
        
        self.__details['name'] = name
        self.__details['full_name'] = full_name
        self.__details['gender'] = gender
        self.__details['maritial_status'] = maritial_status
        self.__details['passport_number'] = passport_number
        self.__details['date_of_birth'] = date_of_birth
        self.__details['email'] = email
        self.__details['mobile_number'] = mobile
        self.__details['skills'] = skills
        self.__details['nationality'] = nationality
        self.__details['languages'] = languages
        self.__details['No. of companies'] = num_of_companies
        self.__details['hobbies'] = hobbies
        self.__details['education'] = edu
        self.__details['address'] = address
        self.__details['state'] = states
        self.__details['pin'] = pincodes
        self.__details['city'] = cities
        self.__details['experience'] = experience
        try:
            #self.__details['experience'] = entities['experience']
            try:
                self.__details['competencies'] ='none'
                utils.extract_competencies(self.__text_raw, entities['experience'])
                self.__details['measurable_results'] ='none'
                utils.extract_measurable_results(self.__text_raw, entities['experience'])
                self.__details['total_experience'] = round(utils.get_total_experience(entities['experience']) / 12, 2)
            except KeyError:
                self.__details['competencies'] = {}
                self.__details['measurable_results'] = {}
                self.__details['total_experience'] = 0
        except KeyError:
            self.__details['competencies'] = {}
            self.__details['measurable_results'] = {}
            self.__details['total_experience'] = 0
        self.__details['no_of_pages'] = {}#utils.get_number_of_pages(self.__resume)

        #comented by vishal sharma 11/8/2019
        '''
        if len( self.__details['city'])>1:
            cities  = utils.extract_cities_exceptional(self.__nlp, self.__noun_chunks,self.__details['city'])
            self.__details['city'] = cities
        '''
        if len( self.__details['pin'])>1:
            pincodes   = utils.extract_pin_exceptional(self.__nlp, self.__noun_chunks,self.__details['pin'])
            self.__details['pin'] = pincodes
        
        return

def resume_result_wrapper(resume):
        parser = ResumeParser(resume)
        return parser.get_extracted_data()

if __name__ == '__main__':
    pool = mp.Pool(mp.cpu_count())

    resumes = []
    data = []
    for root, directories, filenames in os.walk('resumes'):
        for filename in filenames:
            file = os.path.join(root, filename)
            resumes.append(file)

    results = [pool.apply_async(resume_result_wrapper, args=(x,)) for x in resumes]

    results = [p.get() for p in results]

    pprint.pprint(results)
