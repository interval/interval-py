/* eslint-env node */
const { serialize, deserialize } = require('superjson')

process.stdin.on('data', data => {
	process.stdout.write(
		JSON.stringify(
			serialize(deserialize(JSON.parse(data)))
		)
	)

	process.exit(0)
})

