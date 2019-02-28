from smmbapi import GetCourseByID
import pprint

s = GetCourseByID("312E-0000-0392-605E")
nice = pprint.pformat(s)
print(nice)
print(type(nice))
