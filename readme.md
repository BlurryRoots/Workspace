# corsica - Minimalistic CORS and rewrite http dev server

usage: corsica [-h] [--port port] [--host host] [--config config] root

## Options

### port

Specifies port to host server on.

### host

Specifies the hostname (e.g. 127.0.0.1) to host server on.

### config

Path to corsica config file.



## Config

The origin path is defined as a regular expression.

Simple rewrites.

```json
{
	"rewrites": {
		"/readme": "/readme.md",
		"/license": "/license.md"
	}
}
```

For more complex rules, you can use named groups.
Reference the group name via pythons template variable syntax.

```json
{
	"rewrites": {
		"/(?P<mdfiles>readme|license)": "/${mdfiles}.md",
		"/readme|license)": "/${mdfiles}.md"
	}
}
```