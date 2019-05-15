#for namespace_name in $current_class.namespace_list
namespace ${namespace_name} {
#end for

#set ClassName = $current_class.qtscript_class_name

#set has_base_parent = $current_class.base_parent is not None
#if $has_base_parent
	#set ParentClassName = $current_class.base_parent.qtscript_class_name
	#set construct_object_type = $current_class.root_base_parent.namespaced_class_name
#else
	#set native_object_type = $current_class.class_name
	#if $current_class.has_virtual_destructor
		#set $native_object_type += '* '
	#end if
	#set ParentClassName = '::QtScriptBaseClassPrototype<{}>'.format($native_object_type)
	#set construct_object_type = $ClassName + '::NativeObjectType'
#end if

${ClassName}::${ClassName}(QScriptEngine *engine, const QString &className)
	: ${ParentClassName}(engine, className))
{
}

${ClassName}::${ClassName}(QScriptEngine *engine)
	: ${ClassName}(engine, "${current_class.target_class_name}")
{
}

void ${ClassName}::Register(const QScriptValue &targetNamespace)
{
	auto engine = targetNamespace.engine();
	Q_ASSERT(engine);
#if $has_base_parent
	auto inherit = engine->defaultPrototype(qMetaTypeId<${current_class.base_parent.class_name} *>());
#else
	auto inherit = engine->globalObject().property("Object").property("prototype");
#end if
	auto ctor = RegisterT<${current_class.class_name}, ${ClassName}>(targetNamespace, inherit);
	Q_ASSERT(ctor.isFunction());
#for m in $current_class.static_methods_clean():
	ctor.setProperty("${m['name']}", engine->newFunction(
		static_cast<QScriptValue (*)(QScriptContext *, QScriptEngine *)>(
			&${ClassName}::${m['name']})),
			QScriptValue::ReadOnly | QScriptValue::Undeletable);
#end for
}

#if not $current_class.has_constructor:
int ${ClassName}::constructorArgumentCountMin() const
{
	return 0;
}

int ${ClassName}::constructorArgumentCountMax() const
{
	return 0;
}

${construct_object_type} *${ClassName}::constructObject(QScriptContext *context) const
{
	QtScriptEngineUtils::noPublicConstructorException(context,
		"${current_class.namespaced_class_name}");
	return nullptr;
}

#end if