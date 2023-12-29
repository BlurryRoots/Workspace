venver () {
	[ $# -lt 1 ] && {
		echo "USAGE: $0 [command]\n"
			"commands:"
			"\tactivate\n"
			"\tdeactivate\n"
		return 1
	}

	case $1 in
		create|c)
			echo "?"
		;;

		activate|a)
			local possible_venv="$(realpath -s $2)"

			if [ ! -e "${possible_venv}/bin/activate" ]; then
				echo "Theres no venv at $1"
				return 1
			fi

			echo "Activating ${possible_venv} ..."
			source "${possible_venv}/bin/activate"
			source "$HOME/.zshrc"

			return 0
		;;

		deactivate|d)
			if declare -f deactivate > /dev/null; then
				local prev_venv="$VIRTUAL_ENV"
				deactivate
				echo "Deactivated venv at '${prev_venv}' ..."
				source "$HOME/.zshrc"
				return 0
			fi

			echo "No venv activate!"
			return 1
		;;

		info|i)
			if [ -n "$VIRTUAL_ENV" ]; then
				echo $(basename "$VIRTUAL_ENV")
				return 0
			fi

			return 1
		;;

		*)
		;;
	esac
}
