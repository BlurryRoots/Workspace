# Based on bira theme

setopt prompt_subst

() {

local PR_USER PR_USER_OP PR_PROMPT PR_HOST

# Check the UID
if [[ $UID -ne 0 ]]; then # normal user
  PR_USER='%F{128}%n%f'
  PR_USER_OP='%F{159}%#%f'
  PR_PROMPT='%f➤ %f'
else # root
  PR_USER='%F{red}%n%f'
  PR_USER_OP='%F{red}%#%f'
  PR_PROMPT='%F{red}➤ %f'
fi

# Check if we are on SSH or not
if [[ -n "$SSH_CLIENT"  ||  -n "$SSH2_CLIENT" ]]; then
  PR_HOST='%F{red}%M%f' # SSH
else
  PR_HOST='%F{214}%M%f' # no SSH
fi


local return_code="%(?..%F{red}%? ↵%f)"
local user_host="${PR_USER}%F{10FF33}@${PR_HOST}"
local current_dir="%B%F{128}%~%f%b"
local rvm_ruby=''
if ${HOME}/.rvm/bin/rvm-prompt &> /dev/null; then # detect user-local rvm installation
  rvm_ruby='%F{red}‹$(${HOME}/.rvm/bin/rvm-prompt i v g s)›%f'
elif which rvm-prompt &> /dev/null; then # detect system-wide rvm installation
  rvm_ruby='%F{red}‹$(rvm-prompt i v g s)›%f'
elif which rbenv &> /dev/null; then # detect Simple Ruby Version Management
  rvm_ruby='%F{red}‹$(rbenv version | sed -e "s/ (set.*$//")›%f'
fi

get_status_symbol () {
  local status_symbol="🖥️  "

  local git_branch="$(git_prompt_info)"
  local git_c=${#git_branch}
  if (( 0 != ${git_c} )); then
    status_symbol="🌐 "
  fi

  echo ${status_symbol}
}

local current_venv="$(venver info)"
if [[ 0 -ne ${#current_venv} ]]; then
  current_venv="py:${current_venv}"
fi

local status_symbol='$(get_status_symbol)'
local branch='$(git_prompt_info)'

PROMPT="|${status_symbol}${user_host} ${current_dir} ${rvm_ruby} ${branch} ${current_venv}
|$PR_PROMPT "
RPROMPT="${return_code}"

ZSH_THEME_GIT_PROMPT_PREFIX="%F{yellow}‹"
ZSH_THEME_GIT_PROMPT_SUFFIX="› %f"

}
