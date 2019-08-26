from resume_parser import ResumeParser

hobbies = ''
language = ''
pin_code = ''

resume_list=['Amey Bhandare.pdf','ca manoj k  jain.docx','neeraj goel.docx','Resume krunal.docx','Resume.docx','sandeep chandaliya.pdf','Vishal Sharma.docx']
#resume_list = ["sandeep chandaliya.pdf"]
hobbies_list = []
language_list = []
pin_code_list = []

for i in range(len(resume_list)):
  print(resume_list[i])
  print('==========================================================')
  first_name = ''
  middle_name = ''
  last_name = ''
  dob = ''
  gender = ''
  nationality = ''
  marital_status = ''
  passport = ''
  hobbies=''
  hobbies_list.clear()
  language = ''
  language_list.clear()
  address = ''
  landmark = ''
  state = ''
  pin_code = ''
  pin_code_list.clear()
  
  try:
    data = ResumeParser('resumes/'+resume_list[i]).get_extracted_data()
    print(data)
    name = data['full_name']
    dob = data['date_of_birth']
    hobbies_list = data['hobbies']
    language_list = data['languages']
    if type(data['pin']) == type([]):
      pin_code_list = data['pin']
      if len(pin_code_list)>0:  
        pin_code = pin_code_list[0]   
      else: 
        pin_code = 'NA'
    else:
      pin_code=data['pin']

    first_name = name[0]
    middle_name = name[1]
    last_name = name[2]
    dob = data['date_of_birth']
    gender = data['gender']
    nationality = data['nationality']
    marital_status = data['maritial_status']
    passport = data['passport_number']

    if len(hobbies_list)>0:

      for i in range(len(hobbies_list)):
        hobbies = hobbies+hobbies_list[i]+","

    else:
      hobbies = 'NA'

    if len(language_list)>0:

      for i in range(len(language_list)):
        language = language+language_list[i]+","

    else:
      language = 'NA'

    address = data['address']
    landmark = data['city']
    state = data['state']      
    mobile = data['mobile_number']
    email = data['email']


    
  except:
    continue


        
