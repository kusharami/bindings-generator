void qtscript_register_all_${prefix}(QScriptEngine* engine)
{
#if $target_ns
	auto globalObject = engine->globalObject();
	auto targetNamespace = globalObject.property("${target_ns}");
	if (!targetNamespace.isObject())
	{
		targetNamespace = engine->newObject();
		globalObject.setProperty("${target_ns}", targetNamespace,
			QScriptValue::ReadOnly | QScriptValue::Undeletable);
	}
#else
	auto &targetNamespace = engine->globalObject();
#end if
#for cls in $sorted_classes()
	#if $cls.base_parent is not None and $cls.is_code_generated
	${cls.namespace_name}${cls.qtscript_class_name}::Register(targetNamespace);
	#end if
#end for
}
