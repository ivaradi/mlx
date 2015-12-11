# needed for os specific separators
import os
# selenium is needed for browser manipulation
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import NoSuchWindowException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
# urllib is needed to obtain the xml
import urllib2
# xmlparser
from lxml import etree
from StringIO import StringIO
import lxml.html
import time


class MavaSimbriefIntegrator():
    """Implements the integration with the excellent Simbrief pilot briefing
    system for MALEV Virtual."""

    # Progress stage: searching the suitable browser window
    PROGRESS_SEARCHING_BROWSER = 1

    # Progress stage: retrieving the form from the server
    PROGRESS_LOADING_FORM = 2

    # Progress stage: filling the form
    PROGRESS_FILLING_FORM = 3

    # Progress stage: waiting for the login
    PROGRESS_WAITING_LOGIN = 4

    # Progress stage: logging in
    PROGRESS_LOGGING_IN = 5

    # Progress stage: waiting for result
    PROGRESS_WAITING_RESULT = 6

    # The maximal reserved progress stage
    PROGRESS_MAX = 16

    # Result code: none (i.e. the SimBrief query is in progress).
    RESULT_NONE = 0

    # Result code: success
    RESULT_OK = 1

    # Result code: other error
    RESULT_ERROR_OTHER = 2

    # Result code: form could not be loaded
    RESULT_ERROR_NO_FORM = 11

    # Result code: no popup (i.e. login) window found
    RESULT_ERROR_NO_POPUP = 12

    # Result code: login failed
    RESULT_ERROR_LOGIN_FAILED = 13

    # The maximal reserved result code
    RESULT_MAX = 32

    def __init__(self,
                 plan,
                 driver=None,
                 simbrief_query_settings=None,
                 mava_simbrief_url=None,
                 xml_link_fix_part=None):
        """Init the integrator with settings that are typical of our use.
        @param: plan - flightplan dictionary
        @param: webdriver - a selenium webdriver
        @param: simbrief_query_settings - a dictionary of query settings
        @param: mava_simbrief_url - url to the form that is sent to simbrief
        on the mava server
        @param: xml_link_fix_part = url to the simbrief website under which the
        xml is to be found"""
        self.plan = plan
        if simbrief_query_settings is None:
            self.simbrief_query_settings = {
                'navlog': True,
                'etops': True,
                'stepclimbs': True,
                'tlr': True,
                'notams': True,
                'firnot': True,
                'maps': 'Simple',
            }
        else:
            self.simbrief_query_settings = simbrief_query_settings

        if driver is None:
            self.driver = webdriver.Firefox()
        else:
            self.driver = driver

        if mava_simbrief_url is None:
            self.mava_simbrief_url = "http://flare.privatedns.org/" \
                                     "mava_simbrief/simbrief_form.html"
        else:
            self.mava_simbrief_url = mava_simbrief_url

        if xml_link_fix_part is None:
            self.xml_link_fix_part = "http://www.simbrief.com/ofp/" \
                                     "flightplans/xml/"
        else:
            self.xml_link_fix_part = xml_link_fix_part

    def fill_form(self,
                  plan,
                  simbrief_query_settings):
        """Fills the form of the webpage using the paramteres that the class
        has been initialized with.
        @param: driver - a selenium webdriver
        @param: plan - dictionary containing plan details
        @param: simbrief_query_settings - dictionary containing plan settings"""
        for plan_input_field in plan.iterkeys():
            self.driver.find_element_by_name(plan_input_field).send_keys(
                plan[plan_input_field])
        for option_checkbox in simbrief_query_settings.iterkeys():
            if (isinstance(simbrief_query_settings[option_checkbox], bool) and
                    simbrief_query_settings[option_checkbox]):
                # if setting is a boolean type and true
                self.driver.find_element_by_name(option_checkbox).click()
            elif isinstance(simbrief_query_settings[option_checkbox], str):
                # if setting is a select
                Select(self.driver.find_element_by_name(option_checkbox)).\
                    select_by_visible_text(simbrief_query_settings[
                    option_checkbox])

    def get_xml_link(self,
                     get_credentials, update_progress,
                     local_xml_debug=False,
                     local_html_debug=False):
        """Obtains the link of the xml to be processed.
        @param get_credentials - a function, which should return a pair of the
        user name and password to log in to SimBrief. It gets an integer which
        is the number of times it has been called so far.
        @param local_xml_debug - if True then not the real location will be
        checked but the current working dir will be searched for 'xml.xml'
        @param local_html_debug - if True then not real mava_simbrief_url will
        be used but the current working dir will be searched for
        'mava_simbrief.html'
        @returns: the string of the xml link if it could be obtained and None
        otherwise"""
        # Finding xml_link
        is_briefing_available = False
        if local_xml_debug:
            # set link for locally debugging an existing xml file
            xml_link = ("file://"
                        + os.getcwd()
                        + os.sep
                        + "xml.xml")
            is_briefing_available = True
        else:
            update_progress(MavaSimbriefIntegrator.PROGRESS_SEARCHING_BROWSER,
                            MavaSimbriefIntegrator.RESULT_NONE, None)
            # There must be window whose title is 'SimBrief' so that we
            # could find our one among several
            if self._find_window_by_title("SimBrief") is None:
                print "No SimBrief window was found!"
                update_progress(MavaSimbriefIntegrator.PROGRESS_SEARCHING_BROWSER,
                                MavaSimbriefIntegrator.RESULT_ERROR_OTHER, None)
                return None

            # normal operation with a real xml file
            update_progress(MavaSimbriefIntegrator.PROGRESS_LOADING_FORM,
                            MavaSimbriefIntegrator.RESULT_NONE, None)
            if local_html_debug:
                self.driver.get(
                    "file://" + os.getcwd() + os.sep + "simbrief_form.html")
                is_briefing_available = True
            else:
                self.driver.get(self.mava_simbrief_url)

            main_handle = self._find_window_by_title("Malev Virtual Simbrief Integration System")
            if main_handle is None:
                print "No SimBrief Integration window was found!"
                update_progress(MavaSimbriefIntegrator.PROGRESS_LOADING_FORM,
                                MavaSimbriefIntegrator.RESULT_ERROR_NO_FORM, None)
                return None

            # Make a copy of the window handles before submitting the form,
            # so that we could find the popup
            handles = self.driver.window_handles[:]

            # Entering form data
            update_progress(MavaSimbriefIntegrator.PROGRESS_FILLING_FORM,
                            MavaSimbriefIntegrator.RESULT_NONE, None)
            self.driver.switch_to_window(main_handle)
            self.fill_form(self.plan,
                           self.simbrief_query_settings)

            # Loading page
            button = self.driver.find_element_by_name("submitform")
            button.send_keys(Keys.RETURN)

            update_progress(MavaSimbriefIntegrator.PROGRESS_WAITING_LOGIN,
                            MavaSimbriefIntegrator.RESULT_NONE, None)
            popup_handle = self._find_popup(handles)
            if popup_handle is None:
                update_progress(MavaSimbriefIntegrator.PROGRESS_WAITING_LOGIN,
                                MavaSimbriefIntegrator.RESULT_ERROR_NO_POPUP, None)
                return None

            login_count = 0
            end_time = time.time() + 120.0
            while not is_briefing_available and end_time > time.time():
                try:
                    self.driver.switch_to.window(popup_handle)

                    userElement = self.driver.find_element_by_name("user")

                    if userElement is not None:
                        update_progress(MavaSimbriefIntegrator.PROGRESS_LOGGING_IN,
                                        MavaSimbriefIntegrator.RESULT_NONE, None)
                        (userName, password) = get_credentials(login_count)
                        end_time = time.time() + 120.0
                        if userName is None or password is None:
                            update_progress(MavaSimbriefIntegrator.PROGRESS_WAITING_LOGIN,
                                            MavaSimbriefIntegrator.RESULT_ERROR_LOGIN_FAILED, None)
                            return None

                        userElement.send_keys(userName)
                        self.driver.find_element_by_name("pass").send_keys(password)
                        self.driver.find_element_by_name("staylogged").click()

                        self.driver.find_element(By.XPATH,
                                                "//input[@value='Login']").send_keys(Keys.RETURN)
                        login_count += 1
                except NoSuchElementException:
                    pass
                except NoSuchWindowException:
                    pass

                update_progress(MavaSimbriefIntegrator.PROGRESS_WAITING_RESULT,
                                MavaSimbriefIntegrator.RESULT_NONE, None)
                self.driver.switch_to.window(main_handle)
                try:
                    if self.driver.find_element_by_name("hidden_is_briefing_available") is not None:
                        is_briefing_available = True
                        xml_link_element = self.driver.find_element_by_name(
                            'hidden_link')
                        xml_link_generated_part = xml_link_element.get_attribute(
                            'value')
                        xml_link = self.xml_link_fix_part + xml_link_generated_part + '.xml'
                        print(xml_link)
                except NoSuchElementException:
                    pass

        if is_briefing_available:
            return xml_link
        else:
            update_progress(MavaSimbriefIntegrator.PROGRESS_WAITING_RESULT,
                            MavaSimbriefIntegrator.RESULT_ERROR_OTHER, None)
            return None

    def get_results(self,
                    xml_link,
                    html_file_path = None):
        """Parses the xml for information.
        @param xml_link - a path to the xml file
        @return a dictionary of the found information"""
        # Setup variables
        ## Holds analysis data not used
        available_info = {}
        ## Holds analysis data to be used
        flight_info = {}
        ## Holds notams
        notams_list = []
        ## Notam counter
        i = 0
        # Obtaining the xml
        response = urllib2.urlopen(xml_link)
        xml_content = response.read()
        # Processing xml
        tree = etree.parse(StringIO(xml_content))
        context = etree.iterparse(StringIO(xml_content))
        for action, element in context:
            # Processing tags that occur multiple times
            ## NOTAMS
            if element.tag == 'notamdrec':
                notams_element_list = list(element)
                notam_dict = {}
                for notam in notams_element_list:
                    notam_dict[notam.tag] = notam.text
                notams_list.append(notam_dict)
                i += 1
            ## WEATHER
            elif element.tag == 'weather':
                weather_element_list = list(element)
                for weather in weather_element_list:
                    flight_info[weather.tag] = weather.text
            else:
                available_info[element.tag] = element.text
        # Processing plan_html
        ## Obtaining chart links
        image_links = []
        for image_link_a_element in lxml.html.find_class(
                available_info['plan_html'], 'ofpmaplink'):
            for image_link_tuple in image_link_a_element.iterlinks():
                if image_link_tuple[1] == 'src':
                    image_links.append(image_link_tuple[2])
        flight_info['image_links'] = image_links
        print(sorted(available_info.keys()))
        if html_file_path is None:
            html_file_path = 'simbrief_plan.html'
        with open(html_file_path, 'w') as f:
            f.write(available_info['plan_html'])
        return flight_info

    def _find_window_by_title(self, title, timeout = 10.0):
        """Find the window with the given title.

        Switch to that window and return its handle."""
        def predicate(handle):
            self.driver.switch_to.window(handle)
            return self.driver.title == title

        return self._find_window(predicate, timeout = timeout)

    def _find_popup(self, handles, timeout = 10.0):
        """Find a popup, i.e. a new window being created.

        handles is a list of window handles that existed before the popup was
        expected to be created. If a new handle is found, that is assumed to be
        the popup window."""
        return self._find_window(lambda handle: handle not in handles,
                                 timeout = timeout)

    def _find_window(self, predicate, timeout = 10.0):
        """Find a window that fulfills the given predicate."""
        window_handle = None
        end_time = time.time() + timeout
        while window_handle is None and end_time > time.time():
            for handle in self.driver.window_handles:
                if predicate(handle):
                    window_handle = handle
                    break

        return window_handle

if __name__ == "__main__":
    mava_simbrief_url = "http://flare.privatedns.org/" \
                        "mava_simbrief/simbrief_form.html"
    xml_link_fix_part = "http://www.simbrief.com/ofp/" \
                        "flightplans/xml/"
    plan = {
        'airline': 'MAH',
        'fltnum': '764',
        'type': 'B738',
        'orig': 'LHBP',
        'dest': 'LSZH',
        'date': '25FEB15',
        'deph': '20',
        'depm': '00',
        'route': 'GILEP DCT ARSIN UL851 SITNI UL856 NEGRA',
        'steh': '22',
        'stem': '05',
        'reg': 'HA-LOC',
        'fin': 'LOC',
        'selcal': 'XXXX',
        'pax': '100',
        'altn': 'LSGG',
        'fl': '36000',
        'cpt': 'BALINT SZEBENYI',
        'pid': 'P008',
        'fuelfactor': 'P000',
        'manualzfw': '42.7',
        'addedfuel': '2.5',
        'contpct': '0.05',
        'resvrule': '45',
        'taxiout': '10',
        'taxiin': '4',
        'cargo': '5.0',
        'origrwy': '31L',
        'destrwy': '34',
        'climb': '250/300/78',
        'descent': '80/280/250',
        'cruise': 'LRC',
        'civalue': 'AUTO',
    }
    integrator = MavaSimbriefIntegrator(plan=plan)
    link = integrator.get_xml_link(local_xml_debug=False,
                                   local_html_debug=False)
    flight_info = integrator.get_results(link)
    print(flight_info)

