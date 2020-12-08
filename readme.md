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

Configures the rewrite rules.

```json
{
	"rewrites": {
		"/readme": "/readme.md",
		"/license": "/license.md"
	}
}
```
