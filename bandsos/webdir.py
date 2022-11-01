#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
Ref:

- Github REST API: https://docs.github.com/en/rest
- GHAPI: https://ghapi.fast.ai/fullapi.html
- pygit2: https://www.pygit2.org/index.html 

'''
import shutil
import os
from subprocess import check_call
from urllib.error import HTTPError
import warnings
import typing
from ghapi.all import GhApi
import logging

class GithubDirectory:
    def __init__(self, fdir:typing.Union[str, bytes, os.PathLike], username:str, access_token:str, license='mit'):
        '''
        fdir: rootdir/dirname
        '''
        self.rootdir = os.path.dirname(fdir) 
        self.dirname = os.path.basename(fdir)  
        self.username = username # github username
        self.access_token = access_token # github access key
        self.online = False
        self.page_activated = False
        self.local = False
        self.license = license

        self.git = shutil.which('git')
        if self.git is None:
            raise Exception('No git installation if found. Check your PATH.')

        # Check if the folder exists online already
        self.ghapi = GhApi(owner=self.username, repo=self.dirname, token=self.access_token)
        try:
            repo = self.ghapi.repos.get()
            logging.info(f'Found {self.username}/{self.dirname} online!')
            self.online = True
        except HTTPError as e:
            # 404 not found
            # 403 forbidden
            # 301 moved parmanantly
            if e.code == 404 or e.code == 301:
                self.online = False
            else:
                raise HTTPError(code=e.code, msg='Access forbidden! Check your access_token.')

        # If it does not exist online, create
        if not self.online:
            try:
                repo = self.ghapi.repos.create_for_authenticated_user(name=self.dirname, license_template=self.license)
                logging.info(f'Created github directory {self.username}/{self.dirname}')
            except HTTPError as e:
                # 201 Created
                # 304 Not modified
                # 400 Bad Request
                # 401 Requires authentication
                # 403 Forbidden
                # 404 Resource not found
                # 422 Validation failed, or the endpoint has been spammed.
                raise HTTPError(code=e.code, msg='Github folder creation failed! Fatal error!')

        # Then create locally
        if not os.path.exists(self.fdir):
            os.mkdir(self.fdir)
        
        # Initialize git repository
        try:
            check_call([self.git, 'init'], cwd=self.fdir)
        except Exception as e:
            logging.error(e)

        # Check if online branch exists, if exists pull, else create a dummy readme, and push to start the branch
        try:
            branches = self.ghapi.list_branches()
        except HTTPError as e:
            raise HTTPError(code=e.code, msg=f'Can not access {self.username}/{self.dirname} to check branch.')

        if len(branches) == 0:
            check_call(['echo', f'{self.license}', '>', 'LICENSE'], cwd=self.fdir) # a license file
            check_call(['git', 'add', 'LIENCE'], cwd=self.fdir)
            check_call(['git', 'commit', '-m', 'Initialize repository'], cwd=self.fdir)

        try:
            check_call(['git', 'remote', 'add', 'origin', f'https://{self.access_token}@github.com/{self.username}/{self.dirname}.git'], cwd=self.fdir)
        except:
            try:
                check_call(['git', 'remote', 'set-url', 'origin', f'https://{self.access_token}@github.com/{self.username}/{self.dirname}.git'], cwd=self.fdir)
            except Exception as e:
                raise e

        check_call(['git', 'branch', '-M', 'main'], cwd=self.fdir)

        if len(branches) == 0:
            check_call(['git', 'push', '--set-upstream', 'origin', 'main'], cwd=self.fdir)
        else:
            check_call(['git', 'pull', 'origin', 'main'], cwd=self.fdir)
            check_call(['git', 'push', '--set-upstream', 'origin', 'main'], cwd=self.fdir)

        # Then activate the github pages
        try:
            page = self.ghapi.repos.get_pages()
            self.page_activated = True
            logging.info(f'Github pages already published at {page["html_url"]}')
        except:
            # 404 Not found
            page = self.ghapi.repos.create_pages_site(source={'branch':'main'})
            logging.info(f'Github page is now published at {page["html_url"]}')
        
        # Then try to enforce https
        try:
            self.ghapi.repos.update_information_about_pages_site(https_enforced=True)
        except Exception as e:
            logging.info(f'Github pages https_enforced failed with exception {e}')
        else:
            logging.info(f'Github pages https_enforced is now set to True')


    @property
    def fdir(self):
        return(os.path.join(self.rootdir, self.dirname))

    def add(self, fpaths:list, message:str):
        for fpath in fpaths:
            check_call(['git', 'add', fpath], cwd=self.fdir)
        
        check_call(['git', 'commit', '-m', message], cwd=self.fdir)
        check_call(['git', 'push', '--force'], cwd=self.fdir)
        