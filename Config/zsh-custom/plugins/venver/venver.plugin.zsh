venver () {
	[ $# -lt 1 ] && {
		echo "missing command (activate, deactivate)"
		return 1
	}

	if [ "$1" = "activate" ]; then
		if [ ! -e "$2/bin/activate" ]; then
			echo "Theres no venv at $1"
			return 1
		fi

		echo "Activating $2"
		source "$2/bin/activate"
		source "$HOME/.zshrc"

		return 0
	fi

	if [ "$1" = "deactivate" ]; then		
		if declare -f deactivate > /dev/null; then
			local prev_venv="$VIRTUAL_ENV"
			deactivate
			echo "deactivated venv at $prev_venv"
			source "$HOME/.zshrc"
			return 0
		else
			echo "No venv activate!"
			return 1
		fi
	fi

}

venver_info () { 
	if [ -n "$VIRTUAL_ENV" ]; then
		echo $(basename "$VIRTUAL_ENV")
		return 0
	else
		return 1
	fi
}