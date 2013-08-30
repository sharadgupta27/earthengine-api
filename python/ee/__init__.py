"""The EE Javascript library."""



# Using lowercase function naming to match the JavaScript names.
# pylint: disable=g-bad-name

import datetime
import numbers
import sys

import oauth2client.client

from apifunction import ApiFunction
from collection import Collection
from computedobject import ComputedObject
from customfunction import CustomFunction
import data
from ee_exception import EEException
import ee_types as types
from encodable import Encodable
from feature import Feature
from featurecollection import FeatureCollection
from filter import Filter
from function import Function
from geometry import Geometry
from image import Image
from imagecollection import ImageCollection
from serializer import Serializer
from ee_string import String


OAUTH2_SCOPE = 'https://www.googleapis.com/auth/earthengine.readonly'

# A list of autogenerated class names added by _InitializeGenerateClasses.
_generatedClasses = []


# A lightweight class that is used as a dictionary with dot notation.
class _AlgorithmsContainer(dict):
  def __getattr__(self, name):
    return self[name]

  def __setattr__(self, name, value):
    self[name] = value

  def __delattr__(self, name):
    del self[name]

# A dictionary of algorithms that are not bound to a specific class.
Algorithms = _AlgorithmsContainer()


def Initialize(credentials=None, opt_url=None):
  """Initialize the EE library.

  If this hasn't been called by the time any object constructor is used,
  it will be called then.  If this is called a second time with a different
  URL, this doesn't do an un-initialization of e.g.: the previously loaded
  Algorithms, but will overwrite them and let point at alternate servers.

  Args:
    credentials: OAuth2 credentials.
    opt_url: The base url for the EarthEngine REST API to connect to.
  """
  data.initialize(credentials, (opt_url + '/api' if opt_url else None), opt_url)
  # Initialize the dynamically loaded functions on the objects that want them.
  ApiFunction.initialize()
  Image.initialize()
  Feature.initialize()
  Collection.initialize()
  ImageCollection.initialize()
  FeatureCollection.initialize()
  Filter.initialize()
  Geometry.initialize()
  String.initialize()
  _InitializeGeneratedClasses()
  _InitializeUnboundMethods()


def Reset():
  """Reset the library. Useful for re-initializing to a different server."""
  data.reset()
  ApiFunction.reset()
  Image.reset()
  Feature.reset()
  Collection.reset()
  ImageCollection.reset()
  FeatureCollection.reset()
  Filter.reset()
  Geometry.reset()
  String.reset()
  _ResetGeneratedClasses()
  global Algorithms
  Algorithms = _AlgorithmsContainer()


def _ResetGeneratedClasses():
  """Remove the dynamic classes."""
  global _generatedClasses

  for name in _generatedClasses:
    ApiFunction.clearApi(globals()[name])
    del globals()[name]
  _generatedClasses = []


def ServiceAccountCredentials(email, key_file=None, key_data=None):
  """Configure OAuth2 credentials for a Google Service Account.

  Args:
    email: The email address of the account for which to configure credentials.
    key_file: The path to a file containing the private key associated with
        the service account.
    key_data: Raw key data to use, if key_file is not specified.

  Returns:
    An OAuth2 credentials object.
  """
  if key_file:
    key_data = open(key_file, 'rb').read()
  return oauth2client.client.SignedJwtAssertionCredentials(
      email, key_data, OAUTH2_SCOPE)


def call(func, *args, **kwargs):
  """Invoke the given algorithm with the specified args.

  Args:
    func: The function to call. Either an ee.Function object or the name of
        an API function.
    *args: The positional arguments to pass to the function.
    **kwargs: The named arguments to pass to the function.

  Returns:
    A ComputedObject representing the called function. If the signature
    specifies a recognized return type, the returned value will be cast
    to that type.
  """
  if isinstance(func, basestring):
    func = ApiFunction.lookup(func)
  return func.call(*args, **kwargs)


def apply(func, named_args):  # pylint: disable=redefined-builtin
  """Call a function with a dictionary of named arguments.

  Args:
    func: The function to call. Either an ee.Function object or the name of
        an API function.
    named_args: A dictionary of arguments to the function.

  Returns:
    A ComputedObject representing the called function. If the signature
    specifies a recognized return type, the returned value will be cast
    to that type.
  """
  if isinstance(func, basestring):
    func = ApiFunction.lookup(func)
  return func.apply(named_args)


def _Promote(arg, klass):
  """Wrap an argument in an object of the specified class.

  This is used to e.g.: promote numbers or strings to Images and arrays
  to Collections.

  Args:
    arg: The object to promote.
    klass: The expected type.

  Returns:
    The argument promoted if the class is recognized, otherwise the
    original argument.
  """
  if arg is None:
    return arg

  if klass == 'Image':
    return Image(arg)
  elif klass == 'ImageCollection':
    return ImageCollection(arg)
  elif klass in ('Feature', 'EEObject'):
    if isinstance(arg, Collection):
      # TODO(user): Decide whether we want to leave this in. It can be
      #              quite dangerous on large collections.
      return ApiFunction.call_(
          'Feature', ApiFunction.call_('Collection.geometry', arg))
    elif klass == 'EEObject' and isinstance(arg, Image):
      # An Image is already an EEObject.
      return arg
    else:
      return Feature(arg)
  elif klass == 'Geometry':
    if isinstance(arg, Collection):
      return ApiFunction.call_('Collection.geometry', arg)
    else:
      return Geometry(arg)
  elif klass in ('FeatureCollection', 'EECollection', 'Collection'):
    if isinstance(arg, Collection):
      return arg
    else:
      return FeatureCollection(arg)
  elif klass == 'Filter':
    return Filter(arg)
  elif klass == 'ErrorMargin' and isinstance(arg, numbers.Number):
    return ApiFunction.call_('ErrorMargin', arg, 'meters')
  elif klass == 'Algorithm' and isinstance(arg, basestring):
    return ApiFunction.lookup(arg)
  elif klass == 'Date':
    if isinstance(arg, basestring):
      try:
        import dateutil.parser    # pylint: disable=g-import-not-at-top
      except ImportError:
        raise EEException(
            'Conversion of strings to dates requires the dateutil library.')
      else:
        return dateutil.parser.parse(arg)
    elif isinstance(arg, numbers.Number):
      return datetime.datetime.fromtimestamp(arg / 1000)
    else:
      return arg
  elif klass == 'Dictionary':
    if klass not in globals():
      # No dictionary class defined.
      return arg
    cls = globals()[klass]
    if isinstance(arg, cls):
      return arg
    elif isinstance(arg, ComputedObject):
      return cls(arg)
    else:
      # Can't promote non-ComputedObjects up to Dictionary; no constructor.
      return arg
  elif klass == 'String':
    if (types.isString(arg) or
        isinstance(arg, ComputedObject) or
        isinstance(arg, String) or
        types.isVarOfType(arg, String)):
      return String(arg)
    else:
      return arg
  elif klass in globals():
    cls = globals()[klass]
    # Handle dynamically created classes.
    if isinstance(arg, cls):
      return arg
    elif isinstance(arg, basestring):
      if not hasattr(cls, arg):
        raise EEException('Unknown algorithm: %s.%s' % (klass, arg))
      return getattr(cls, arg)()
    else:
      return cls(arg)
  else:
    return arg


def _InitializeUnboundMethods():
  # Sort the items by length, so parents get created before children.
  items = ApiFunction.unboundFunctions().items()
  items.sort(key=lambda x: len(x[0]))

  for name, func in items:
    signature = func.getSignature()
    if signature.get('hidden', False):
      continue

    # Create nested objects as needed.
    name_parts = name.split('.')
    target = Algorithms
    while len(name_parts) > 1:
      first = name_parts[0]
      if not hasattr(target, first):
        setattr(target, first, _AlgorithmsContainer())
      target = getattr(target, first)
      name_parts = name_parts[1:]

    # Attach the function.
    # We need a copy of the function to attach properties.
    # pylint: disable=unnecessary-lambda
    bound = lambda *args, **kwargs: func.call(*args, **kwargs)
    # pylint: enable=unnecessary-lambda
    bound.signature = signature
    bound.__doc__ = str(func)
    setattr(target, name_parts[0], bound)


def _InitializeGeneratedClasses():
  """Generate classes for extra types that appear in the web API."""
  signatures = ApiFunction.allSignatures()
  # Collect the first part of any function names that contain a '.'.
  names = set([name.split('.')[0] for name in signatures if '.' in name])
  # Collect the return types of all functions.
  returns = set([signatures[sig]['returns'] for sig in signatures])
  # We generate classes for all return types that match algorithms names TYPE.x
  # excluding those already handled by the client library, and those
  # explicitly blacklisted.
  blacklist = ['List']
  want = [name for name in names.intersection(returns)
          if name not in globals() and name not in blacklist]

  for name in want:
    globals()[name] = _MakeClass(name)
    _generatedClasses.append(name)


def _MakeClass(name):
  def init(self, *args):
    """Initializer for dynamically created classes.

    Args:
      self: The instance of this class.  Listed to make the linter hush.
      *args: Either a ComputedObject to be promoted to this type, or
             arguments to an algorithm with the same name as this class.

    Returns:
      The new class.
    """
    if isinstance(args[0], ComputedObject) and len(args) == 1:
      result = args[0]
    else:
      result = ApiFunction.call_(name, *args)

    ComputedObject.__init__(self, result.func, result.args)

  new_class = type(str(name), (ComputedObject,), {'__init__': init})
  ApiFunction.importApi(new_class, name, name)
  return new_class


# Set up type promotion rules as soon the package is loaded.
Function._registerPromoter(_Promote)   # pylint: disable=protected-access
