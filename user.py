import sys # to use sys.stdout
import os
from datetime import datetime
from time import strftime
import datetime
import json
import urllib2
import argparse
import base64
import pprint
import requests    
import string
from urlparse import urlparse, parse_qs

def printf(format, *args):
    sys.stdout.write(format % args)
def githubDateToUSdate(date):
    dt = datetime.strptime(date, "%Y-%m-%dT%H:%M:%SZ")
    return dt

if hasattr(__builtins__, 'raw_input'): 
    input = raw_input

# Turn off console output buffering
buf_arg = 0
if sys.version_info[0] == 3:
    os.environ['PYTHONUNBUFFERED'] = '1'
    buf_arg = 1
try:
    sys.stdout = os.fdopen(sys.stdout.fileno(), 'a+', buf_arg)
    sys.stderr = os.fdopen(sys.stderr.fileno(), 'a+', buf_arg)
except:
    pass
    
parser = argparse.ArgumentParser(description='''
List all repository of a GitHub organization.''')
parser.add_argument('-u',metavar='USER', dest='github_user', action='store', required=False,
    help='GitHub user',
    default=None)
parser.add_argument('-p',metavar='PASSWORD', dest='github_pass', action='store', required=False,
    help='GitHub password',
    default=None)
parser.add_argument('-o',metavar='ORG', dest='github_org', action='store', required=False,
    help='GitHub organization to list. Default %(default)s',
    default='D4UDigitalPlatform')
parser.add_argument('-w',metavar='WEEKS', dest='weeks', action='store', required=False,
    help='Time of interests, in weeks. Default %(default)s',
    default='52')
parser.add_argument('--repo',metavar='REPONAME', dest='repo', action='store', required=False,
    help='GitHub repository name (without orga name)',
    default=None)
parser.add_argument('--userdetails', dest='repo', action='store', required=False,
    help='Show detailed information about each organization users',
    default=False)
parser.add_argument('--url',metavar='URL', dest='github_url', action='store', required=False,
    help='GitHub API url. Default %(default)s',
    default='https://api.github.com')


args = parser.parse_args()
if (args.github_user == None):
    args.github_user = input("GitHub Username :")
if (args.github_pass == None):
    print "GitHub Password (sorry, it will be displayed in the console. Use -p instead"
    args.github_pass = input(":")
time_of_interest_in_weeks = int(args.weeks)
time_of_interest_in_weeks_absolute = datetime.datetime.today() - datetime.timedelta(weeks = time_of_interest_in_weeks)
base64string = base64.b64encode(args.github_user + ':' + args.github_pass )
#headers = {"Authorization": "Basic %s" % base64string, "Accept": "application/vnd.github.inertia-preview+json"}
headers = {"Authorization": "Basic %s" % base64string, "Accept": "application/vnd.github.mercy-preview+json"}


printf("Find inactive user :\n\tSince %s\n\tFor organization %s\n\tFor %s repo\n\tUsing authent provided by %s\n",
	time_of_interest_in_weeks_absolute,
	args.github_org,
	"all" if args.repo == None else args.repo,
	args.github_user
	)



url = args.github_url + "/orgs/" + args.github_org
print "Get organization information ..."

res=requests.get(url,headers=headers)
if (res.status_code <> 200):
    printf("ERROR : API reply HTTP code %d\n", res.status_code)
    sys.exit(res.status_code)
repos=res.json()
printf("Organization informations :\n")
printf("\tDisk usage        : %d\n", repos.get("disk_usage"))
printf("\tTotal privat repo : %d\n", repos.get("total_private_repos"))
printf("\tCollaborators     : %d\n", repos.get("collaborators"))
printf("\tPlan name         : %s\n", repos.get("plan")['name'])
printf("\tPlan max repo     : %d\n", repos.get("plan")['private_repos'])
printf("\tPlan used space   : %d\n", repos.get("plan")['space'])

#
#See https://developer.github.com/v3/repos/#list-organization-repositories
#
url = args.github_url + "/orgs/"+args.github_org+"/members?per_page=100"
print "Get all users member of the organization"
members = [] # all members subscribe to the orga
activemembers = [] # all orga members with activity
inactivemembers = []# all orga member without activity

def get_user_info(login):
	url = args.github_url + "/users/" + login
	res=requests.get(url,headers=headers)
	mem=res.json()
	return ({
		'login': mem.get('login'),
		'location': "" if (mem.get('location')==None) else mem.get('location').encode('utf-8').encode('ascii', 'backslashreplace'),
		'name':"" if (mem.get('name') == None) else mem.get('name').encode('ascii', 'backslashreplace'),
		'email': "" if (mem.get('email') == None) else mem.get('email'),
		'created_at':mem.get('created_at')
	})

# create the members list containing all member subribing the orga
while True:
	res=requests.get(url,headers=headers)
	mem=res.json()
	for member in mem:
		login = member.get('login')
		members.append(login)
		#info = get_user_info(login)
		#printf("%s;%s;%s;%s;%s\n", info.get('login'), info.get('location'), info.get('name'), info.get('email'), info.get('created_at'))
	printf("%d members fetched...\r", len(members))
	if 'next' in res.links.keys():
		url = res.links['next']['url']
	else:
		break

printf("Found %d members       \n", len(members))

def get_contributors_from_contributors_url(url, headers):
	contributors = []
	while True:
		res=requests.get(url+"?per_page=100",headers=headers)
		if (res.status_code == 204):
			break
		ctr=res.json()
		for contributor in ctr:
			contributors.append({
				'login':contributor.get('login'),
				'contributions':contributor.get('contributions')
			})
		#printf("%d contributors fetched...\r", len(contributors))
		if 'next' in res.links.keys():
			url = res.links['next']['url']
		else:
			break	
	return contributors

def get_nbcommits_from(url, author, since, header):
	url = string.replace(url, "{/sha}", "")
	url = url + "?per_page=1&since="+since.isoformat()+"&author="+author # Do I need urlencode here ?
	nbcommits = 0
	res=requests.get(url,headers=headers)
	com = res.json()
	nbcommits = len(com)
	if (len(com) != 0):
		prevurl = res.links['last']['url']
		parsed_url = urlparse(prevurl)
		qs = parse_qs(parsed_url.query)
		nbcommits = int(qs.get('page')[0])
	return nbcommits
	
def get_commits_from(url, author, since, header):
	# {/sha}
	url = string.replace(url, "{/sha}", "")
	url = url + "?per_page=100&since="+since.isoformat()
	if (author != None):
		url = url + "&author="+author # Do I need urlencode here ?
	commits=[]
	while True:
		res=requests.get(url,headers=headers)
		com = res.json()
		if (res.status_code == 409):
			return []
		for commit in com:
			author = "" if (commit.get('author') == None) else commit.get('author').get('login')
			committer = commit.get('commit').get('committer').get('name')
			commit_author = commit.get('commit').get('author').get('name')
			committer_login = "" if (commit.get('committer') == None) else commit.get('committer').get('login')
			sha = commit.get('sha')
			if author == "" or author == None:
				author = committer_login
			if author == "" or author == None:
				author = commit_author
			if author == "" or author == None:
				author = committer
			
			#printf("%s %s %s %s %s\n", sha, author, committer, commit_author, committer_login)
			commits.append({
				'login':author.encode('ascii', 'backslashreplace'),
				'sha':sha,
				'date':commit.get('commit').get('committer').get('date')
			})
		if 'next' in res.links.keys():
			url = res.links['next']['url']
		else:
			break	
	return commits


# for each repo of the orga,
# fetch all commits since a date.
# for each commit, extract committer and add it to the active list if he is memeber of the orga
print "Get all users of repo of the organization"
url = args.github_url + "/orgs/"+args.github_org+"/repos?type=all&per_page=100"
repos = []
nonmembers = []
while True:
	res=requests.get(url,headers=headers)
	rep=res.json()
	for repo in rep:
		reponame = repo.get('name')
		repos.append(reponame)
		printf("- %s\n", reponame)
		if (args.repo == None or reponame == args.repo):
			commits = get_commits_from(repo.get('commits_url'), None, time_of_interest_in_weeks_absolute, headers) #Get all commits since a date
			printf("\tFound %5d commits ", len(commits))
			
			nbcommit_by_login = {}
			for com in commits:
				login = com.get('login')
				if (login in nbcommit_by_login) :
					nbcommit_by_login[login] = nbcommit_by_login[login] + 1
				else :
					nbcommit_by_login[login] = 1
			printf("by %d users\n", len(nbcommit_by_login))
			for login,nbcom in sorted(nbcommit_by_login.iteritems(), key=lambda (k,v): (v,k), reverse=True):
				printf("\t\t%20s : %5d commits", login, nbcom)
				if (login in members):
					if  (login not in activemembers):
						activemembers.append(login)
				else:
					printf(" not in organization")
				printf("\n")
			'''
			contributors_url = repo.get('contributors_url')
			contributors = get_contributors_from_contributors_url(contributors_url, headers)
			printf("\t%d contributors :\n", len(contributors))
			for c in contributors:
				login = c.get('login')
				printf("\t\t%20s (%5d total contributions) ", login, c.get('contributions'))
				if login not in members and login not in nonmembers:
					nonmembers.append(login)
#				if login not in activemembers and login in members:
#					activemembers.append(login)
				#commits = get_commits_from(repo.get('commits_url'), login, time_of_interest_in_weeks_absolute, headers)
				#printf("%5d commits\n", len(commits))
				if (login in members):
					nbcommit = get_nbcommits_from(repo.get('commits_url'), login, time_of_interest_in_weeks_absolute, headers)
					#if (nbcommit > 0):
					#	printf("had commited\n")
					#else:
					#	printf("did not commit\n")
					printf("%4d commits\n", nbcommit)
				else:
					printf("not in organization\n")
				if (nbcommit > 0 and login in members and login not in activemembers):
					activemembers.append(login)
			printf("\n")
			'''
	if 'next' in res.links.keys():
		url = res.links['next']['url']
	else:
		break

inactivemembers = members
for m in activemembers:
	inactivemembers.remove(m)

printf("Found %4d members of the organization\n", len(members))
printf("Found %4d contributors not existing anymore in organization\n", len(nonmembers))
printf("Found %4d active member of the organization\n", len(activemembers))
printf("Found %4d inactive member of the organization :\n", len(inactivemembers))
for m in inactivemembers:
	printf("%s\n", m)
