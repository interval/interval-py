/* eslint-env node */
const { default: superjson } = require('superjson')

superjson.registerCustom({
	name: 'time',
	isApplicable: v => typeof v === 'string' && /^\d{2}:\d{2}:\d{2}$/.test(v),
	serialize: v => v,
	deserialize: v => v,
}, 'time')

process.stdin.on('data', data => {
	process.stdout.write(
		JSON.stringify(
			superjson.serialize(superjson.deserialize(JSON.parse(data)))
		)
	)

	process.exit(0)
})

