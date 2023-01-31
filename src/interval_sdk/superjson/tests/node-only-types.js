/* eslint-env node */
const { serialize } = require('superjson')

process.stdout.write(
	JSON.stringify(
		serialize({
			'map': new Map([[1, 2], ['a', 'b']]),
		})
	)
)

process.exit(0)

