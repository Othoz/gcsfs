#!/bin/bash
set -ev

echo TRAVIS_REPO_SLUG is set to "$TRAVIS_REPO_SLUG"
echo TRAVIS_PULL_REQUEST is set to "$TRAVIS_PULL_REQUEST"
if [ "$TRAVIS_PULL_REQUEST" = "false" ]; then
  echo PR is an internal PR coming from "$TRAVIS_REPO_SLUG".
  openssl aes-256-cbc -K "$encrypted_c49b49c0ca67_key" -iv "$encrypted_c49b49c0ca67_iv" -in .travis/service-account-key.json.enc -out "$HOME"/service-account-key.json -d
  export GOOGLE_APPLICATION_CREDENTIALS=$HOME/service-account-key.json
  export TEST_BUCKET=othoz-gcsfs-tests
  pytest --cov=fs_gcsfs --cov-branch --cov-report=xml --numprocesses=16
else
  echo PR coming from "$TRAVIS_REPO_SLUG". Not running test suite as it requires credentials that are not available when running a PR from a forked repo.
fi